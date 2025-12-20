#!/usr/bin/env python3
"""
MCP Client with LLM Integration - Functional Version

This client combines an LLM (GPT) with MCP server capabilities using a functional approach:
- LLM dynamically discovers available MCP tools/resources/prompts
- LLM decides when and how to use MCP capabilities
- Shows transparent MCP operations to the user
- Gracefully falls back to pure LLM if MCP fails

Usage:
1. Start the MCP server: python fastmcp_quickstart.py
2. Run this client: python mcp_client_basic_func.py
3. Ask questions and watch the LLM use MCP when helpful
"""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI
from pydantic import AnyUrl

from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client


def setup_openai() -> OpenAI:
    """Set up OpenAI client using the API key file."""
    OPENAI_API_KEY_FILE = "openai_api_key.txt"
    try:
        with open(OPENAI_API_KEY_FILE, 'r') as f:
            api_key = f.read().strip()
        
        if not api_key.startswith("sk-"):
            print(f"❌ Invalid API key found in '{OPENAI_API_KEY_FILE}'")
            sys.exit(1)
            
        client = OpenAI(api_key=api_key)
        print("✅ OpenAI client initialized")
        return client
        
    except FileNotFoundError:
        print(f"❌ API key file '{OPENAI_API_KEY_FILE}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error setting up OpenAI: {e}")
        sys.exit(1)


async def connect_to_mcp(server_url: str = "http://localhost:8000/mcp") -> Tuple[Optional[ClientSession], Any]:
    """Connect to MCP server and return session."""
    try:
        print(f"🔌 Connecting to MCP server at {server_url}...")
        client_context = streamablehttp_client(server_url)
        read_stream, write_stream, _ = await client_context.__aenter__()
        session = ClientSession(read_stream, write_stream)
        await session.__aenter__()
        await session.initialize()
        
        print("✅ MCP server connected")
        return session, client_context
        
    except Exception as e:
        print(f"⚠️  MCP server unavailable: {e}")
        print("🤖 Continuing with LLM-only mode...")
        return None, None


async def discover_mcp_capabilities(session: ClientSession) -> Tuple[List[types.Tool], List[types.Resource], List[types.ResourceTemplate], List[types.Prompt]]:
    """Discover all available MCP capabilities."""
    try:
        # Discover tools
        tools_response = await session.list_tools()
        available_tools = tools_response.tools
        
        # Discover resources
        resources_response = await session.list_resources()
        available_resources = resources_response.resources
        
        # Discover resource templates
        templates_response = await session.list_resource_templates()
        resource_templates = templates_response.resourceTemplates
        
        # Discover prompts
        prompts_response = await session.list_prompts()
        available_prompts = prompts_response.prompts
        
        print(f"🔍 Discovered: {len(available_tools)} tools, {len(available_resources)} resources, {len(resource_templates)} resource templates, {len(available_prompts)} prompts")
        
        return available_tools, available_resources, resource_templates, available_prompts
        
    except Exception as e:
        print(f"⚠️  Error discovering capabilities: {e}")
        return [], [], [], []


def build_capability_description(tools: List[types.Tool], 
                                resources: List[types.Resource], 
                                resource_templates: List[types.ResourceTemplate], 
                                prompts: List[types.Prompt]) -> str:
    """Build a description of available MCP capabilities for the LLM."""
    if not any([tools, resources, resource_templates, prompts]):
        return "No MCP server available."
    
    description = "Available MCP capabilities:\n\n"
    
    # Describe tools
    if tools:
        description += "TOOLS (functions you can call):\n"
        for tool in tools:
            description += f"- {tool.name}: {tool.description}\n"
            if tool.inputSchema and "properties" in tool.inputSchema:
                props = tool.inputSchema["properties"]
                params = [f"{name}({info.get('type', 'unknown')})" for name, info in props.items()]
                description += f"  Parameters: {', '.join(params)}\n"
        description += "\n"
    
    # Describe resource templates (dynamic resources)
    if resource_templates:
        description += "RESOURCE TEMPLATES (dynamic data you can read):\n"
        for template in resource_templates:
            description += f"- {template.uriTemplate}: {template.description}\n"
        description += "\n"
    
    # Describe static resources
    if resources:
        description += "STATIC RESOURCES (fixed data you can read):\n"
        for resource in resources:
            description += f"- {resource.uri}: {resource.name}\n"
        description += "\n"
    
    # Describe prompts
    if prompts:
        description += "PROMPTS (templates you can use):\n"
        for prompt in prompts:
            description += f"- {prompt.name}: {prompt.description}\n"
            if prompt.arguments:
                args = [f"{arg.name}({'required' if arg.required else 'optional'})" for arg in prompt.arguments]
                description += f"  Arguments: {', '.join(args)}\n"
        description += "\n"
    
    return description


async def call_llm_with_mcp_context(openai_client: OpenAI, user_prompt: str, capability_description: str) -> str:
    """Call the LLM with context about available MCP capabilities."""
    if not openai_client:
        return "❌ OpenAI client not available"
    
    system_prompt = f"""You are an AI assistant with access to MCP (Model Context Protocol) capabilities.

{capability_description}

INSTRUCTIONS:
1. Analyze the user's question to see if any MCP capabilities could help answer it
2. If MCP capabilities are relevant, respond ONLY with the JSON format below (no other text)
3. If no MCP capabilities are relevant, answer the question normally (no JSON)

When using MCP capabilities, respond with ONLY this JSON format:
{{
    "reasoning": "Why I'm using MCP capabilities",
    "mcp_operations": [
        {{
            "type": "tool|resource|prompt",
            "name": "operation_name", 
            "parameters": {{"param1": "value1"}}
        }}
    ],
    "needs_mcp": true
}}

IMPORTANT: When you need to use MCP, respond with ONLY the JSON above - no explanations or additional text."""
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            top_p=0.5,
            frequency_penalty=0.5,
            presence_penalty=0.5
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        return f"❌ Error calling LLM: {e}"


async def execute_mcp_operation(session: ClientSession, operation: Dict[str, Any]) -> str:
    """Execute a single MCP operation."""
    if not session:
        return "❌ MCP server not available"
    
    op_type = operation.get("type")
    name = operation.get("name")
    parameters = operation.get("parameters", {})
    
    try:
        if op_type == "tool":
            print(f"🔧 Calling tool: {name} with {parameters}")
            result = await session.call_tool(name, arguments=parameters)
            
            # Extract result content
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
        
        elif op_type == "resource":
            uri = name  # For resources, name is the URI
            print(f"📄 Reading resource: {uri}")
            result = await session.read_resource(AnyUrl(uri))
            
            content_parts = []
            for content in result.contents:
                if isinstance(content, types.TextContent):
                    content_parts.append(content.text)
            return " ".join(content_parts)
        
        elif op_type == "prompt":
            print(f"💭 Getting prompt: {name} with {parameters}")
            result = await session.get_prompt(name, arguments=parameters)
            
            messages = []
            for message in result.messages:
                if hasattr(message, 'content') and isinstance(message.content, types.TextContent):
                    messages.append(f"{message.role}: {message.content.text}")
            return "\n".join(messages)
        
        else:
            return f"❌ Unknown operation type: {op_type}"
            
    except Exception as e:
        return f"❌ MCP operation failed: {e}"


def extract_json_from_response(llm_response: str) -> Optional[str]:
    """Extract JSON content from LLM response, handling various formats."""
    if '"needs_mcp"' not in llm_response:
        return None
    
    # Try to extract JSON from code blocks first
    if '```json' in llm_response:
        start = llm_response.find('```json') + 7
        end = llm_response.find('```', start)
        return llm_response[start:end].strip()
    
    # Try direct JSON parsing
    elif llm_response.strip().startswith('{'):
        return llm_response.strip()
    
    # Look for JSON anywhere in the response (handle nested braces)
    else:
        import re
        # Find JSON blocks more robustly, handling nested structures
        json_matches = re.finditer(r'\{', llm_response)
        for match in json_matches:
            start_pos = match.start()
            brace_count = 0
            end_pos = start_pos
            
            for i, char in enumerate(llm_response[start_pos:], start_pos):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i + 1
                        break
            
            potential_json = llm_response[start_pos:end_pos]
            if '"needs_mcp"' in potential_json:
                return potential_json
    
    return None


async def process_user_input(openai_client: OpenAI, 
                           session: Optional[ClientSession], 
                           user_input: str, 
                           capability_description: str) -> str:
    """Process user input, potentially using MCP capabilities."""
    print(f"\n🤔 Processing: {user_input}")
    print("="*60)
    
    # Get LLM response with MCP context
    llm_response = await call_llm_with_mcp_context(openai_client, user_input, capability_description)
    
    # Check if LLM wants to use MCP
    json_content = extract_json_from_response(llm_response)
    
    if json_content and session:
        try:
            # Parse JSON response from LLM
            mcp_request = json.loads(json_content)
        
            if mcp_request.get("needs_mcp"):
                print(f"🧠 LLM reasoning: {mcp_request.get('reasoning', 'Not specified')}")
                
                # Execute MCP operations
                mcp_results = []
                for operation in mcp_request.get("mcp_operations", []):
                    result = await execute_mcp_operation(session, operation)
                    mcp_results.append(result)
                
                # Get final response from LLM using MCP results
                final_prompt = f"""Based on the MCP operation results below, provide a comprehensive answer to the user's question: "{user_input}"

MCP Results:
{chr(10).join(f"- {result}" for result in mcp_results)}

Provide a clear, helpful response to the user."""
                
                final_response = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": final_prompt}],
                    temperature=0.2
                )
                
                return final_response.choices[0].message.content.strip()
            
        except json.JSONDecodeError as e:
            print(f"⚠️  LLM response wasn't valid JSON: {e}")
            print(f"⚠️  Response content: {llm_response[:200]}...")
        except Exception as e:
            print(f"⚠️  Error processing MCP request: {e}")
    
    # Return regular LLM response
    return llm_response


async def disconnect_from_mcp(session: Optional[ClientSession], client_context: Any):
    """Disconnect from MCP server."""
    if session and client_context:
        try:
            await session.__aexit__(None, None, None)
            await client_context.__aexit__(None, None, None)
            print("🔌 Disconnected from MCP server")
        except Exception as e:
            print(f"⚠️  Error during disconnect: {e}")


async def main():
    """Main interactive loop."""
    print("🚀 MCP Client with LLM Integration (Functional Version)")
    print("="*60)
    
    # Setup OpenAI client
    openai_client = setup_openai()
    
    # Try to connect to MCP server
    session, client_context = await connect_to_mcp()
    
    # Discover MCP capabilities
    if session:
        tools, resources, resource_templates, prompts = await discover_mcp_capabilities(session)
        capability_description = build_capability_description(tools, resources, resource_templates, prompts)
        print("✅ Capabilities discovered")
    else:
        capability_description = "No MCP server available."
        print("📝 Note: MCP features will not be available")
    
    print("\n💡 Ask me anything! I'll use MCP capabilities when helpful.")
    print("Type 'quit' to exit.")
    
    try:
        while True:
            user_input = input("\n👤 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            if not user_input:
                continue
            
            # Process the user input
            response = await process_user_input(openai_client, session, user_input, capability_description)
            print(f"\n🤖 Assistant: {response}")
    
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    
    finally:
        await disconnect_from_mcp(session, client_context)


if __name__ == "__main__":
    asyncio.run(main())