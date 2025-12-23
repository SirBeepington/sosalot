#!/usr/bin/env python3
"""
Smart LLM Client - Schema-Driven MCP Investigation

Implements the smart client pseudocode with strict JSON schema validation.
The LLM acts as pure planner, client handles orchestration.

Usage:
    python smart_client.py "What network interfaces does centos9-original have?"
"""

import asyncio
import json
import sys
from typing import Dict, List, Any, Optional
import jsonschema

from openai import OpenAI
from pydantic import AnyUrl

from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client


# JSON Schemas for LLM responses
CALL_TOOL_SCHEMA = {
    "type": "object",
    "required": ["action", "tool", "args", "reason"],
    "properties": {
        "action": {"const": "call_tool"},
        "tool": {"type": "string"},
        "args": {"type": "object"},
        "reason": {"type": "string"}
    },
    "additionalProperties": False
}

ASK_USER_SCHEMA = {
    "type": "object",
    "required": ["action", "question", "why"],
    "properties": {
        "action": {"const": "ask_user"},
        "question": {"type": "string"},
        "why": {"type": "string"}
    },
    "additionalProperties": False
}

ANSWER_USER_SCHEMA = {
    "type": "object",
    "required": ["action", "answer"],
    "properties": {
        "action": {"const": "answer_user"},
        "answer": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1}
    },
    "additionalProperties": False
}

ALLOWED_SCHEMAS = [CALL_TOOL_SCHEMA, ASK_USER_SCHEMA, ANSWER_USER_SCHEMA]

# Safety limits
MAX_CONSECUTIVE_TOOL_CALLS = 25  # Max MCP calls before forcing user interaction


class SmartClient:
    """Schema-driven LLM client for MCP server interaction."""
    
    def __init__(self):
        self.openai_client = None
        self.mcp_session = None
        self.client_context = None
        self.tools_description = ""
        self.max_iterations = 20
        
    async def setup(self) -> bool:
        """Setup OpenAI and MCP connections."""
        # Setup OpenAI
        try:
            with open("../keys/openai_api_key.txt", 'r') as f:
                api_key = f.read().strip()
            self.openai_client = OpenAI(api_key=api_key)
            print("✅ OpenAI connected")
        except Exception as e:
            print(f"❌ OpenAI setup failed: {e}")
            return False
            
        # Setup MCP
        try:
            server_url = "http://localhost:8000/mcp"
            self.client_context = streamablehttp_client(server_url)
            read_stream, write_stream, _ = await self.client_context.__aenter__()
            self.mcp_session = ClientSession(read_stream, write_stream)
            await self.mcp_session.__aenter__()
            await self.mcp_session.initialize()
            print("✅ MCP connected")
        except Exception as e:
            print(f"❌ MCP setup failed: {e}")
            return False
            
        # Discover tools
        try:
            self.tools_description = await self._discover_tools()
            print("✅ Tools discovered")
            return True
        except Exception as e:
            print(f"❌ Tool discovery failed: {e}")
            return False
    
    async def _discover_tools(self) -> str:
        """Get tool descriptions for LLM."""
        tools_response = await self.mcp_session.list_tools()
        
        tools_desc = "Available MCP tools:\n\n"
        for tool in tools_response.tools:
            tools_desc += f"**{tool.name}**\n"
            tools_desc += f"Description: {tool.description}\n"
            if tool.inputSchema and "properties" in tool.inputSchema:
                tools_desc += "Parameters:\n"
                for param, info in tool.inputSchema["properties"].items():
                    param_type = info.get("type", "unknown")
                    param_desc = info.get("description", "")
                    tools_desc += f"  - {param} ({param_type}): {param_desc}\n"
            tools_desc += "\n"
        
        return tools_desc
    
    def _validate_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Validate LLM response against allowed schemas."""
        try:
            # Parse JSON
            response_json = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parse error: {e}")
            return None
        
        # Strict schema validation - no auto-correction
        for schema in ALLOWED_SCHEMAS:
            try:
                jsonschema.validate(response_json, schema)
                return response_json  # Valid!
            except jsonschema.ValidationError:
                continue
        
        print(f"⚠️ Protocol violation: {response_json}")
        return None
    
    async def _call_llm(self, question: str, context: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Call LLM with current state and enforce schema compliance."""
        # Build context summary
        context_summary = ""
        if context:
            context_summary = "\nInvestigation history:\n"
            for i, ctx in enumerate(context):
                if "tool" in ctx:
                    result_preview = str(ctx["result"])[:200] + "..." if len(str(ctx["result"])) > 200 else str(ctx["result"])
                    context_summary += f"{i+1}. Tool '{ctx['tool']}': {result_preview}\n"
                elif "user_fact" in ctx:
                    context_summary += f"{i+1}. User clarification: {ctx['user_fact']}\n"
        
        system_prompt = f"""You are an expert system administrator using MCP tools to investigate questions.

{self.tools_description}

PROTOCOL: You MUST respond with exactly one JSON object. Choose ONE of these actions:

1. To use an MCP tool, respond with:
{{"action": "call_tool", "tool": "tool_name", "args": {{"param": "value"}}, "reason": "why I need this data"}}

2. To ask user for clarification:
{{"action": "ask_user", "question": "what do you need to know?", "why": "explanation of why you need this"}}

3. To provide final answer:
{{"action": "answer_user", "answer": "your complete answer", "confidence": 0.9}}

CRITICAL RULES:
- Respond with ONLY the JSON object, no other text
- Be methodical in your investigation
- Don't repeat the same tool call more than twice
- If a tool call fails, try a different approach"""

        user_prompt = f"USER QUESTION: {question}{context_summary}"
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1
                )
                
                response_text = response.choices[0].message.content.strip()
                
                # Try to extract JSON if wrapped in code blocks
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                elif "```" in response_text:
                    json_start = response_text.find("```") + 3
                    json_end = response_text.rfind("```")
                    if json_end > json_start:
                        response_text = response_text[json_start:json_end].strip()
                
                # Validate against schemas
                validated_response = self._validate_response(response_text)
                if validated_response:
                    return validated_response
                
                print(f"⚠️ Invalid response attempt {attempt + 1}: {response_text[:100]}...")
                
            except Exception as e:
                print(f"⚠️ LLM call failed attempt {attempt + 1}: {e}")
        
        print("❌ LLM failed to provide valid response after retries")
        return None
    
    async def _execute_mcp_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Execute MCP tool and return result."""
        try:
            print(f"🔧 Executing: {tool_name} with {args}")
            result = await self.mcp_session.call_tool(tool_name, arguments=args)
            
            # Extract text content
            if result.content:
                content_parts = []
                for content in result.content:
                    if isinstance(content, types.TextContent):
                        content_parts.append(content.text)
                return " ".join(content_parts)
            elif hasattr(result, 'structuredContent') and result.structuredContent:
                return json.dumps(result.structuredContent)
            else:
                return "Tool executed successfully (no output)"
                
        except Exception as e:
            return f"Error executing {tool_name}: {e}"
    
    def _ask_user(self, question: str, why: str) -> str:
        """Ask user for clarification."""
        print(f"\n🤔 {why}")
        return input(f"❓ {question}: ").strip()
    
    async def investigate(self, question: str) -> str:
        """Run the main investigation loop."""
        state = {
            "question": question,
            "context": [],
            "consecutive_tool_calls": 0  # Safety counter
        }
        
        print(f"🚀 Starting investigation: {question}")
        print(f"⚡ Safety limit: Max {MAX_CONSECUTIVE_TOOL_CALLS} consecutive tool calls")
        print("=" * 60)
        
        for iteration in range(self.max_iterations):
            print(f"\n--- Iteration {iteration + 1} ---")
            
            # Get LLM decision
            llm_response = await self._call_llm(state["question"], state["context"])
            if not llm_response:
                return "❌ Investigation failed: LLM could not provide valid response"
            
            action = llm_response["action"]
            print(f"🎯 LLM action: {action}")
            
            # Safety check: prevent runaway tool calling
            if action == "call_tool" and state["consecutive_tool_calls"] >= MAX_CONSECUTIVE_TOOL_CALLS:
                print(f"⚠️ Safety limit reached ({MAX_CONSECUTIVE_TOOL_CALLS} consecutive tool calls)")
                print("🛑 Forcing user interaction to prevent runaway costs")
                return f"Investigation paused after {MAX_CONSECUTIVE_TOOL_CALLS} consecutive tool calls. Please ask a more specific question or use a different approach."
            
            if action == "call_tool":
                state["consecutive_tool_calls"] += 1
                print(f"🔢 Tool call #{state['consecutive_tool_calls']}/{MAX_CONSECUTIVE_TOOL_CALLS}")
                
                tool_result = await self._execute_mcp_tool(
                    llm_response["tool"], 
                    llm_response["args"]
                )
                
                state["context"].append({
                    "tool": llm_response["tool"],
                    "args": llm_response["args"], 
                    "reason": llm_response["reason"],
                    "result": tool_result
                })
                
                # Show result preview
                preview = tool_result[:200] + "..." if len(tool_result) > 200 else tool_result
                print(f"📄 Result: {preview}")
                continue
            
            elif action == "ask_user":
                # Reset safety counter - user interaction happened
                state["consecutive_tool_calls"] = 0
                user_reply = self._ask_user(llm_response["question"], llm_response["why"])
                
                state["context"].append({
                    "user_question": llm_response["question"],
                    "user_fact": user_reply
                })
                continue
            
            elif action == "answer_user":
                confidence = llm_response.get("confidence", "unknown")
                print(f"\n✅ Investigation complete (confidence: {confidence})")
                print(f"📊 Total tool calls made: {state['consecutive_tool_calls']}")
                return llm_response["answer"]
        
        return f"❌ Investigation incomplete after {self.max_iterations} iterations"
    
    async def cleanup(self):
        """Cleanup connections."""
        if self.mcp_session and self.client_context:
            try:
                await self.mcp_session.__aexit__(None, None, None)
                await self.client_context.__aexit__(None, None, None)
            except:
                pass


async def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        question = "What network interfaces does centos9-original have?"
    
    client = SmartClient()
    
    if not await client.setup():
        print("❌ Setup failed")
        return
    
    try:
        answer = await client.investigate(question)
        print("\n" + "=" * 60)
        print("📋 FINAL ANSWER")
        print("=" * 60)
        print(answer)
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())