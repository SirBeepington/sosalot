#!/usr/bin/env python3
"""
Simple LLM MCP Test - Single Question Focus

Tests a single question to see how well the LLM uses MCP tools in practice.
Actually executes the tools and evaluates the final answer.

Usage:
    python simple_llm_test.py "How many network interfaces does centos9-original_20251209_2142 have?"
"""

import asyncio
import json
import sys
from typing import Any, Dict

from openai import OpenAI
from pydantic import AnyUrl

from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client


async def setup_connections():
    """Setup OpenAI and MCP connections."""
    # Setup OpenAI
    try:
        with open("../keys/openai_api_key.txt", 'r') as f:
            api_key = f.read().strip()
        openai_client = OpenAI(api_key=api_key)
        print("✅ OpenAI connected")
    except Exception as e:
        print(f"❌ OpenAI failed: {e}")
        return None, None, None
        
    # Setup MCP
    try:
        server_url = "http://localhost:8000/mcp"
        client_context = streamablehttp_client(server_url)
        read_stream, write_stream, _ = await client_context.__aenter__()
        session = ClientSession(read_stream, write_stream)
        await session.__aenter__()
        await session.initialize()
        print("✅ MCP connected")
        return openai_client, session, client_context
    except Exception as e:
        print(f"❌ MCP failed: {e}")
        return None, None, None


async def discover_tools(session: ClientSession) -> str:
    """Get tool descriptions for LLM."""
    tools_response = await session.list_tools()
    
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


async def execute_mcp_tool(session: ClientSession, tool_name: str, parameters: Dict[str, Any]) -> str:
    """Execute an MCP tool and return the result."""
    try:
        print(f"🔧 Executing: {tool_name} with {parameters}")
        result = await session.call_tool(tool_name, arguments=parameters)
        
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


async def run_single_test(hostname: str, question: str):
    """Run a single test with hostname and question - full realistic workflow."""
    print(f"🧪 Testing hostname: {hostname}")
    print(f"🧪 Question: {question}")
    print("=" * 60)
    
    # Setup
    openai_client, session, client_context = await setup_connections()
    if not openai_client or not session:
        return
    
    try:
        # Get available tools
        tools_description = await discover_tools(session)
        
        # Single prompt that combines hostname and question - realistic user experience
        user_prompt = f"I need to analyze SOS reports for hostname '{hostname}'. {question}"
        
        # Phase 1: Ask LLM to plan the investigation
        planning_prompt = f"""You are a system administrator analyzing SOS reports using MCP tools.

{tools_description}

USER REQUEST: {user_prompt}

INSTRUCTIONS:
1. Plan your investigation to answer the user's question about the specified hostname
2. Respond with ONLY a JSON array of tool calls needed:

[
    {{"tool": "tool_name", "parameters": {{"param": "value"}}}},
    {{"tool": "next_tool", "parameters": {{"param": "value"}}}}
]

Be systematic: discover reports, explore structure, find relevant data."""

        print("🤔 LLM planning investigation...")
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": planning_prompt}],
            temperature=0.1
        )
        
        plan_text = response.choices[0].message.content.strip()
        
        # Parse the plan
        try:
            if "```json" in plan_text:
                json_part = plan_text.split("```json")[1].split("```")[0].strip()
            else:
                json_part = plan_text
            
            tool_plan = json.loads(json_part)
            print(f"📋 LLM planned {len(tool_plan)} tool calls")
            
        except json.JSONDecodeError as e:
            print(f"❌ Could not parse LLM plan: {e}")
            print(f"LLM response: {plan_text}")
            return
        
        # Phase 2: Execute the tools
        tool_results = []
        for i, tool_call in enumerate(tool_plan):
            tool_name = tool_call.get("tool", "")
            parameters = tool_call.get("parameters", {})
            
            result = await execute_mcp_tool(session, tool_name, parameters)
            tool_results.append({
                "tool": tool_name,
                "parameters": parameters,
                "result": result
            })
            
            # Truncate long results for display
            display_result = result[:200] + "..." if len(result) > 200 else result
            print(f"  {i+1}. {tool_name}: {display_result}")
        
        # Phase 3: Get final answer from LLM
        final_prompt = f"""Based on the MCP tool results below, provide a clear, specific answer to the user's request: "{user_prompt}"

Tool Results:
{json.dumps(tool_results, indent=2)}

Provide a concise, factual answer based on the data above."""

        print("\n🤖 LLM analyzing results...")
        final_response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": final_prompt}],
            temperature=0.1
        )
        
        final_answer = final_response.choices[0].message.content.strip()
        
        # Results
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS")
        print("=" * 60)
        print(f"Hostname: {hostname}")
        print(f"Question: {question}")
        print(f"Tools Used: {[call['tool'] for call in tool_plan]}")
        print(f"Final Answer: {final_answer}")
        
        # Simple evaluation
        if tool_results and not any("Error" in str(result["result"]) for result in tool_results):
            print("✅ Test completed successfully")
        else:
            print("⚠️ Some tools had errors")
            
    finally:
        # Cleanup
        if session and client_context:
            try:
                await session.__aexit__(None, None, None)
                await client_context.__aexit__(None, None, None)
            except:
                pass


async def main():
    """Main entry point."""
    if len(sys.argv) >= 3:
        hostname = sys.argv[1]
        question = " ".join(sys.argv[2:])
    else:
        # Default test case
        hostname = "centos9-original"
        question = "What network interfaces does this system have?"
    
    await run_single_test(hostname, question)


if __name__ == "__main__":
    asyncio.run(main())