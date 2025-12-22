#!/usr/bin/env python3
"""
Automated LLM Test Harness for SOSALot

Tests whether LLMs can effectively understand and use the current tool descriptions
to perform common SOS report analysis tasks. Uses the predictable "example" report
for consistent testing.

Usage:
    python llm_test_harness.py

This will run a series of automated tests to evaluate:
- Tool discovery and selection
- Parameter usage  
- Investigation workflows
- Overall effectiveness
"""

import asyncio
import json
import sys
from typing import Dict, List, Any, Tuple

from openai import OpenAI
from pydantic import AnyUrl

from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client


class LLMTestHarness:
    """Automated test harness for evaluating LLM understanding of MCP tools."""
    
    def __init__(self):
        self.openai_client = None
        self.mcp_session = None
        self.client_context = None
        self.test_results = []
        
    async def setup(self):
        """Setup OpenAI and MCP connections."""
        # Setup OpenAI
        try:
            with open("../keys/openai_api_key.txt", 'r') as f:
                api_key = f.read().strip()
            self.openai_client = OpenAI(api_key=api_key)
            print("✅ OpenAI client initialized")
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
            print("✅ MCP server connected")
            return True
        except Exception as e:
            print(f"❌ MCP setup failed: {e}")
            return False
    
    async def discover_capabilities(self) -> str:
        """Get available MCP capabilities for LLM context."""
        tools_response = await self.mcp_session.list_tools()
        available_tools = tools_response.tools
        
        description = "Available MCP tools:\n\n"
        for tool in tools_response.tools:
            description += f"**{tool.name}**: {tool.description}\n"
            if tool.inputSchema and "properties" in tool.inputSchema:
                props = tool.inputSchema["properties"]
                params = [f"{name}({info.get('type', 'unknown')})" for name, info in props.items()]
                description += f"  Parameters: {', '.join(params)}\n"
            description += "\n"
        
        return description
    
    async def run_test_scenario(self, test_name: str, user_question: str, expected_tools: List[str]) -> Dict[str, Any]:
        """Run a single test scenario and evaluate LLM performance."""
        print(f"\n🧪 Running test: {test_name}")
        print(f"Question: {user_question}")
        
        # Get capabilities description
        capabilities = await self.discover_capabilities()
        
        # Create system prompt
        system_prompt = f"""You are an expert system administrator analyzing Linux SOS reports using MCP tools.

{capabilities}

TASK: Answer the user's question about the "example" SOS report using the available tools.

INSTRUCTIONS:
1. Think step by step about what information you need
2. Use the appropriate MCP tools to gather that information  
3. Provide a clear, specific answer based on the data you find

RESPOND WITH: A JSON object containing:
{{
    "reasoning": "Step-by-step explanation of your approach",
    "tool_calls": [
        {{"tool": "tool_name", "parameters": {{"param": "value"}}, "reason": "why using this tool"}}
    ],
    "answer": "Final answer to the user's question"
}}
"""

        # Get LLM response
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_question}
                ],
                temperature=0.1
            )
            
            llm_response = response.choices[0].message.content.strip()
            
            # Try to parse JSON response
            try:
                if llm_response.startswith('```json'):
                    json_content = llm_response.split('```json')[1].split('```')[0].strip()
                else:
                    json_content = llm_response
                
                parsed_response = json.loads(json_content)
                
                # Evaluate the response
                evaluation = self.evaluate_response(parsed_response, expected_tools)
                
                test_result = {
                    "test_name": test_name,
                    "question": user_question,
                    "llm_response": parsed_response,
                    "evaluation": evaluation,
                    "passed": evaluation["overall_score"] >= 0.7
                }
                
                self.test_results.append(test_result)
                return test_result
                
            except json.JSONDecodeError as e:
                print(f"❌ LLM response wasn't valid JSON: {e}")
                test_result = {
                    "test_name": test_name,
                    "question": user_question, 
                    "llm_response": llm_response,
                    "evaluation": {"error": "Invalid JSON response", "overall_score": 0},
                    "passed": False
                }
                self.test_results.append(test_result)
                return test_result
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
            test_result = {
                "test_name": test_name,
                "question": user_question,
                "llm_response": None,
                "evaluation": {"error": str(e), "overall_score": 0},
                "passed": False
            }
            self.test_results.append(test_result)
            return test_result
    
    def evaluate_response(self, response: Dict[str, Any], expected_tools: List[str]) -> Dict[str, Any]:
        """Evaluate how well the LLM used the tools."""
        evaluation = {
            "tool_selection_score": 0,
            "parameter_usage_score": 0,
            "workflow_logic_score": 0,
            "overall_score": 0,
            "feedback": []
        }
        
        tool_calls = response.get("tool_calls", [])
        tools_used = [call.get("tool", "") for call in tool_calls]
        
        # Score tool selection
        expected_set = set(expected_tools)
        used_set = set(tools_used)
        
        if expected_set & used_set:  # Any overlap
            evaluation["tool_selection_score"] = len(expected_set & used_set) / len(expected_set)
            evaluation["feedback"].append(f"✅ Used expected tools: {list(expected_set & used_set)}")
        else:
            evaluation["feedback"].append(f"❌ Expected {expected_tools}, used {tools_used}")
        
        # Score parameter usage (basic check)
        param_score = 0
        for call in tool_calls:
            if call.get("parameters"):
                param_score += 1
        evaluation["parameter_usage_score"] = min(param_score / len(tool_calls), 1.0) if tool_calls else 0
        
        # Score workflow logic (did they start with query_sos_reports?)
        if tool_calls and tool_calls[0].get("tool") == "query_sos_reports":
            evaluation["workflow_logic_score"] = 1.0
            evaluation["feedback"].append("✅ Started with report discovery")
        else:
            evaluation["workflow_logic_score"] = 0.5
            evaluation["feedback"].append("⚠️ Didn't start with query_sos_reports")
        
        # Overall score
        evaluation["overall_score"] = (
            evaluation["tool_selection_score"] * 0.5 +
            evaluation["parameter_usage_score"] * 0.25 +
            evaluation["workflow_logic_score"] * 0.25
        )
        
        return evaluation
    
    async def run_all_tests(self):
        """Run all test scenarios."""
        test_scenarios = [
            {
                "name": "Basic Report Discovery",
                "question": "What SOS reports are available? List them.",
                "expected_tools": ["query_sos_reports"]
            },
            {
                "name": "Network Interface Investigation", 
                "question": "How many network interfaces does the 'centos9-original_20251209_2142' report show?",
                "expected_tools": ["query_sos_reports", "list_dir", "read_file"]
            },
            {
                "name": "System Information Extraction",
                "question": "What operating system and version is running on the 'centos9-original_20251209_2142' system?",
                "expected_tools": ["query_sos_reports", "read_file"]
            },
            {
                "name": "Log Analysis",
                "question": "Are there any errors in the system logs of the 'centos9-original_20251209_2142' report?",
                "expected_tools": ["query_sos_reports", "search_file", "list_dir"]
            }
        ]
        
        print("🚀 Starting Automated LLM Test Suite")
        print("=" * 60)
        
        for scenario in test_scenarios:
            result = await self.run_test_scenario(
                scenario["name"],
                scenario["question"], 
                scenario["expected_tools"]
            )
            
            if result["passed"]:
                print(f"✅ {scenario['name']}: PASSED")
            else:
                print(f"❌ {scenario['name']}: FAILED")
                
            # Show key evaluation points
            if "evaluation" in result and "feedback" in result["evaluation"]:
                for feedback in result["evaluation"]["feedback"]:
                    print(f"   {feedback}")
        
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary."""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for test in self.test_results if test["passed"])
        total = len(self.test_results)
        
        print(f"Tests Passed: {passed}/{total}")
        print(f"Success Rate: {passed/total*100:.1f}%")
        
        # Average scores
        avg_tool_selection = sum(test["evaluation"].get("tool_selection_score", 0) for test in self.test_results) / total
        avg_overall = sum(test["evaluation"].get("overall_score", 0) for test in self.test_results) / total
        
        print(f"Avg Tool Selection Score: {avg_tool_selection:.2f}")
        print(f"Avg Overall Score: {avg_overall:.2f}")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED! Your tool descriptions work well with LLMs.")
        elif avg_overall > 0.6:
            print("\n✅ Good results! Minor improvements possible.")
        else:
            print("\n⚠️ Tool descriptions may need improvement for better LLM understanding.")
        
        print("\n💡 This validates whether your current tool contracts are LLM-friendly!")
    
    async def cleanup(self):
        """Cleanup connections."""
        if self.mcp_session and self.client_context:
            try:
                await self.mcp_session.__aexit__(None, None, None)
                await self.client_context.__aexit__(None, None, None)
            except:
                pass


async def main():
    """Main test runner."""
    harness = LLMTestHarness()
    
    if not await harness.setup():
        print("❌ Setup failed, cannot run tests")
        return
    
    try:
        await harness.run_all_tests()
    finally:
        await harness.cleanup()


if __name__ == "__main__":
    asyncio.run(main())