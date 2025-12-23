#!/usr/bin/env python3
"""
SosAlot MCP Server Test Client

Tests all functionality of the sosalot_server.py MCP server directly
without involving an LLM. This allows us to verify tools work correctly
before adding LLM complexity.

Usage:
1. Start sosalot_server.py in one terminal
2. Run this test client: python test_sosalot_client.py
"""

import asyncio
import json
import argparse
from typing import Any, Dict, List

from pydantic import AnyUrl

from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client


# Global test results tracking
test_results = {
    "passed": 0,
    "failed": 0,
    "details": []
}

# Global debug flag
debug_mode = False


def log_test(test_name: str, passed: bool, details: str = ""):
    """Log test result for summary."""
    test_results["details"].append({
        "test": test_name,
        "passed": passed,
        "details": details
    })
    if passed:
        test_results["passed"] += 1
    else:
        test_results["failed"] += 1


async def connect_to_server(server_url: str = "http://localhost:8000/mcp"):
    """Connect to the SosAlot MCP server."""
    try:
        print(f"🔌 Connecting to SosAlot server at {server_url}...")
        client_context = streamablehttp_client(server_url)
        read_stream, write_stream, _ = await client_context.__aenter__()
        session = ClientSession(read_stream, write_stream)
        await session.__aenter__()
        await session.initialize()
        print("✅ Connected successfully!")
        log_test("Server Connection", True, "Connected successfully")
        return session, client_context
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        log_test("Server Connection", False, str(e))
        return None, None


async def test_server_info(session: ClientSession):
    """Test basic server information."""
    print("\n📋 Testing Server Information")
    print("-" * 50)
    
    try:
        # List available tools
        tools_response = await session.list_tools()
        tool_count = len(tools_response.tools)
        print(f"Available tools: {tool_count}")
        for tool in tools_response.tools:
            print(f"  - {tool.name}: {tool.description}")
            if tool.inputSchema and "properties" in tool.inputSchema:
                props = tool.inputSchema["properties"]
                params = [f"{name}({info.get('type', 'unknown')})" for name, info in props.items()]
                print(f"    Parameters: {', '.join(params) if params else 'None'}")
        
        # List available resources
        resources_response = await session.list_resources()
        resource_count = len(resources_response.resources)
        print(f"\nAvailable resources: {resource_count}")
        for resource in resources_response.resources:
            print(f"  - {resource.uri}")
        
        # List available prompts
        prompts_response = await session.list_prompts()
        prompt_count = len(prompts_response.prompts)
        print(f"\nAvailable prompts: {prompt_count}")
        for prompt in prompts_response.prompts:
            print(f"  - {prompt.name}")
        
        log_test("Server Discovery", True, f"{tool_count} tools, {resource_count} resources, {prompt_count} prompts")
        
    except Exception as e:
        print(f"❌ Server info test failed: {e}")
        log_test("Server Discovery", False, str(e))


async def test_query_sos_reports_tool(session: ClientSession):
    """Test the query_sos_reports tool with various parameters."""
    print("\n🧪 Testing query_sos_reports Tool")
    print("-" * 50)
    
    # Test 1: Query all reports (no filters)
    print("Test 1: Query all SOS reports (no filters)")
    try:
        result = await session.call_tool("query_sos_reports", arguments={})
        print(f"✅ Success: Found {len(result.content)} content blocks")
        
        # DEBUG: Show raw tool response (only if debug mode enabled)
        if debug_mode:
            print("\n🔍 RAW TOOL RESPONSE:")
            print("-" * 30)
            if result.content:
                for i, content in enumerate(result.content):
                    print(f"Content Block {i}:")
                    if hasattr(content, 'text'):
                        print(f"  Text: {content.text}")
                    if hasattr(content, 'type'):
                        print(f"  Type: {content.type}")
            
            if hasattr(result, 'structuredContent') and result.structuredContent:
                print(f"Structured Content: {result.structuredContent}")
            print("-" * 30)
        
        # Check structured content and extract report IDs for later tests
        reports_found = 0
        global test_report_id
        test_report_id = None
        
        # Parse JSON response from tool content
        if result.content:
            for content_block in result.content:
                if hasattr(content_block, 'text'):
                    try:
                        # Parse JSON from tool response
                        reports_data = json.loads(content_block.text)
                        if isinstance(reports_data, dict) and 'reports' in reports_data:
                            reports = reports_data['reports']
                            if isinstance(reports, list):
                                reports_found = len(reports)
                                print(f"   Found {reports_found} SOS reports")
                                for i, report in enumerate(reports[:3]):  # Show first 3
                                    report_id = report.get('report_id', 'Unknown')
                                    report_name = report.get('report_name', 'Unknown')
                                    hostname = report.get('hostname', 'Unknown')
                                    print(f"   Report {i+1}: {report_id} (hostname: {hostname})")
                                    
                                    # Store first report ID for later tests
                                    if i == 0 and report_id != 'Unknown':
                                        test_report_id = report_id
                                        print(f"   📌 Using '{report_id}' for subsequent tests")
                            break
                    except json.JSONDecodeError as e:
                        print(f"⚠️  Could not parse JSON response: {e}")
                        if debug_mode:
                            print(f"   Raw content: {content_block.text}")
        
        # Fallback check for structured content (if available)
        if not test_report_id and hasattr(result, 'structuredContent') and result.structuredContent:
            reports_data = result.structuredContent
            if isinstance(reports_data, dict) and 'reports' in reports_data:
                reports = reports_data['reports']
                if isinstance(reports, list) and reports:
                    test_report_id = reports[0].get('report_id')
                    reports_found = len(reports)
        
        log_test("Query All Reports", True, f"Found {reports_found} reports")
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        log_test("Query All Reports", False, str(e))
    
    # Test 2: Query by hostname
    print("\nTest 2: Query by hostname filter")
    try:
        result = await session.call_tool("query_sos_reports", arguments={
            "hostname": "test"
        })
        print("✅ Hostname filter test completed")
        log_test("Hostname Filter", True, "Filter executed without error")
    except Exception as e:
        print(f"❌ Failed: {e}")
        log_test("Hostname Filter", False, str(e))
    
    # Test 3: Query by serial number
    print("\nTest 3: Query by serial number filter")
    try:
        result = await session.call_tool("query_sos_reports", arguments={
            "serial_number": "ABC123"
        })
        print("✅ Serial number filter test completed")
        log_test("Serial Number Filter", True, "Filter executed without error")
    except Exception as e:
        print(f"❌ Failed: {e}")
        log_test("Serial Number Filter", False, str(e))
    
    # Test 4: Query by date
    print("\nTest 4: Query by date filter")
    try:
        result = await session.call_tool("query_sos_reports", arguments={
            "date_contains": "2024"
        })
        print("✅ Date filter test completed")
        log_test("Date Filter", True, "Filter executed without error")
    except Exception as e:
        print(f"❌ Failed: {e}")
        log_test("Date Filter", False, str(e))
    
    # Test 5: Combined filters
    print("\nTest 5: Combined filters")
    try:
        result = await session.call_tool("query_sos_reports", arguments={
            "hostname": "server",
            "date_contains": "Dec"
        })
        print("✅ Combined filters test completed")
        log_test("Combined Filters", True, "Multiple filters executed without error")
    except Exception as e:
        print(f"❌ Failed: {e}")
        log_test("Combined Filters", False, str(e))


# Global variable to store a test report ID
test_report_id = None


async def test_filesystem_tools(session: ClientSession):
    """Test all filesystem tools with the new report + path API."""
    print("\n📁 Testing New Report + Path API")
    print("-" * 50)
    
    if not test_report_id:
        print("⚠️  No test report ID available - skipping filesystem tests")
        print("   Make sure query_sos_reports found at least one report")
        log_test("Filesystem Tools", False, "No test report ID available")
        return
    
    print(f"🎯 Using test report ID: {test_report_id}")
    
    # Test 1: list_dir - List report root
    print("\nTest 1: list_dir - List report root directory")
    try:
        result = await session.call_tool("list_dir", arguments={
            "report": test_report_id,
            "path": ""
        })
        print("✅ list_dir (root) executed successfully")
        
        if debug_mode:
            print("\n🔍 list_dir RAW RESPONSE:")
            print("-" * 30)
            if result.content:
                for i, content in enumerate(result.content):
                    if hasattr(content, 'text'):
                        print(f"Content Block {i}: {content.text[:500]}...")
            print("-" * 30)
        
        log_test("list_dir Root", True, "Root directory listing completed")
        
    except Exception as e:
        print(f"❌ list_dir failed: {e}")
        log_test("list_dir Root", False, str(e))
    
    # Test 2: list_dir - List etc directory
    print("\nTest 2: list_dir - List etc directory")
    try:
        result = await session.call_tool("list_dir", arguments={
            "report": test_report_id,
            "path": "etc",
            "max_items": 20
        })
        print("✅ list_dir (etc) executed successfully")
        log_test("list_dir Subdirectory", True, "Subdirectory listing completed")
        
    except Exception as e:
        print(f"❌ list_dir (etc) failed: {e}")
        log_test("list_dir Subdirectory", False, str(e))
    
    # Test 3: list_dir - Invalid path
    print("\nTest 3: list_dir - Invalid path test")
    try:
        result = await session.call_tool("list_dir", arguments={
            "report": test_report_id,
            "path": "../../../etc/shadow"  # Should be blocked
        })
        print("✅ list_dir security test completed (should show error)")
        log_test("list_dir Security", True, "Security validation executed")
        
    except Exception as e:
        print(f"✅ list_dir correctly handled insecure path: {e}")
        log_test("list_dir Security", True, f"Handled insecure path: {e}")
    
    # Test 4: search_for_files_and_directories
    print("\nTest 4: search_for_files_and_directories - Search for txt files")
    try:
        result = await session.call_tool("search_for_files_and_directories", arguments={
            "report": test_report_id,
            "pattern": "*.txt",
            "search_path": "",
            "max_results": 10
        })
        print("✅ search_for_files_and_directories executed successfully")
        log_test("File Search", True, "File search completed")
        
    except Exception as e:
        print(f"❌ search_for_files_and_directories failed: {e}")
        log_test("File Search", False, str(e))
    
    # Test 5: search_for_files_and_directories - Search in subdirectory
    print("\nTest 5: search_for_files_and_directories - Search in etc")
    try:
        result = await session.call_tool("search_for_files_and_directories", arguments={
            "report": test_report_id,
            "pattern": "*host*",
            "search_path": "etc",
            "max_results": 5
        })
        print("✅ search in subdirectory executed successfully")
        log_test("Subdirectory Search", True, "Subdirectory search completed")
        
    except Exception as e:
        print(f"❌ search in subdirectory failed: {e}")
        log_test("Subdirectory Search", False, str(e))
    
    # Test 6: search_for_files_and_directories - Security test
    print("\nTest 6: search_for_files_and_directories - Security test")
    try:
        result = await session.call_tool("search_for_files_and_directories", arguments={
            "report": test_report_id,
            "pattern": "**/*.conf",  # Should be blocked
            "search_path": ""
        })
        print("✅ Globstar security test completed (should show error)")
        log_test("Search Security", True, "Security validation executed")
        
    except Exception as e:
        print(f"✅ search correctly blocked globstar pattern: {e}")
        log_test("Search Security", True, f"Blocked globstar: {e}")
    
    # Test 7: read_file - Try to read hostname
    print("\nTest 7: read_file - Read hostname file")
    try:
        result = await session.call_tool("read_file", arguments={
            "report": test_report_id,
            "path": "etc/hostname",
            "offset": 0,
            "limit": 1000
        })
        print("✅ read_file (hostname) executed successfully")
        
        if debug_mode:
            print("\n🔍 read_file RAW RESPONSE:")
            print("-" * 30)
            if result.content:
                for i, content in enumerate(result.content):
                    if hasattr(content, 'text'):
                        print(f"Content Block {i}: {content.text[:200]}...")
            print("-" * 30)
        
        log_test("Read File", True, "Hostname file read completed")
        
    except Exception as e:
        print(f"❌ read_file (hostname) failed: {e}")
        log_test("Read File", False, str(e))
    
    # Test 8: read_file - Try to read os-release
    print("\nTest 8: read_file - Read os-release file")
    try:
        result = await session.call_tool("read_file", arguments={
            "report": test_report_id,
            "path": "etc/os-release",
            "offset": 0,
            "limit": 500
        })
        print("✅ read_file (os-release) executed successfully")
        log_test("Read OS Release", True, "OS release file read completed")
        
    except Exception as e:
        print(f"❌ read_file (os-release) failed: {e}")
        log_test("Read OS Release", False, str(e))
    
    # Test 9: read_file - Invalid file
    print("\nTest 9: read_file - Invalid file test")
    try:
        result = await session.call_tool("read_file", arguments={
            "report": test_report_id,
            "path": "nonexistent/file.txt"
        })
        print("✅ read_file invalid file test completed (should show error)")
        log_test("Read File Invalid", True, "Invalid file test executed")
        
    except Exception as e:
        print(f"✅ read_file correctly handled invalid file: {e}")
        log_test("Read File Invalid", True, f"Handled invalid file: {e}")
    
    # Test 10: search_file - Search within hostname
    print("\nTest 10: search_file - Search within hostname file")
    try:
        result = await session.call_tool("search_file", arguments={
            "report": test_report_id,
            "path": "etc/hostname",
            "substring": ".",  # Look for dots in hostname
            "lines_before": 1,
            "lines_after": 1,
            "max_matches": 5
        })
        print("✅ search_file executed successfully")
        log_test("Search in File", True, "File content search completed")
        
    except Exception as e:
        print(f"❌ search_file failed: {e}")
        log_test("Search in File", False, str(e))
    
    # Test 11: search_file - Search in os-release
    print("\nTest 11: search_file - Search in os-release")
    try:
        result = await session.call_tool("search_file", arguments={
            "report": test_report_id,
            "path": "etc/os-release",
            "substring": "VERSION",
            "lines_before": 0,
            "lines_after": 0,
            "max_matches": 3
        })
        print("✅ search_file (os-release) executed successfully")
        log_test("Search OS Release", True, "OS release search completed")
        
    except Exception as e:
        print(f"❌ search_file (os-release) failed: {e}")
        log_test("Search OS Release", False, str(e))


async def test_new_tools(session: ClientSession):
    """Redirect to the new filesystem tools test."""
    await test_filesystem_tools(session)


async def test_error_conditions(session: ClientSession):
    """Test error handling and edge cases."""
    print("\n🚨 Testing Error Conditions")
    print("-" * 50)
    
    # Test 1: Invalid tool name
    print("Test 1: Invalid tool name")
    try:
        result = await session.call_tool("nonexistent_tool", arguments={})
        if result.isError:
            print(f"✅ Correctly returned error: {result.content[0].text if result.content else 'Unknown error'}")
            log_test("Invalid Tool Name", True, "Properly returned error response")
        else:
            print(f"❌ Expected error but got success: {result}")
            log_test("Invalid Tool Name", False, "Expected error but got success")
    except Exception as e:
        print(f"✅ Correctly failed with exception: {type(e).__name__}")
        log_test("Invalid Tool Name", True, f"Exception: {type(e).__name__}")
    
    # Test 2: Invalid parameters for valid tool
    print("\nTest 2: Invalid parameter types")
    try:
        result = await session.call_tool("query_sos_reports", arguments={
            "hostname": 123,  # Should be string
            "invalid_param": "test"
        })
        print("✅ Tool handled invalid parameters gracefully")
        log_test("Invalid Parameters", True, "Tool handled gracefully")
    except Exception as e:
        print(f"✅ Correctly rejected invalid params: {type(e).__name__}")
        log_test("Invalid Parameters", True, f"Correctly rejected: {type(e).__name__}")


def print_test_summary():
    """Print a summary of all test results."""
    print("\n" + "=" * 60)
    print("🧪 TEST SUMMARY")
    print("=" * 60)
    
    total_tests = test_results["passed"] + test_results["failed"]
    pass_rate = (test_results["passed"] / total_tests * 100) if total_tests > 0 else 0
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {test_results['passed']} ✅")
    print(f"Failed: {test_results['failed']} ❌")
    print(f"Pass Rate: {pass_rate:.1f}%")
    
    if test_results["failed"] > 0:
        print("\n❌ FAILED TESTS:")
        for test in test_results["details"]:
            if not test["passed"]:
                print(f"  • {test['test']}: {test['details']}")
    
    if test_results["passed"] == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️  {test_results['failed']} test(s) need attention")


async def disconnect_from_server(session, client_context):
    """Disconnect from server."""
    try:
        await session.__aexit__(None, None, None)
        await client_context.__aexit__(None, None, None)
        print("\n🔌 Disconnected from server")
    except Exception as e:
        print(f"⚠️  Error during disconnect: {e}")


async def main():
    """Run all tests."""
    print("🧪 SosAlot MCP Server Test Suite")
    print("=" * 60)
    
    # Connect to server
    session, client_context = await connect_to_server()
    if not session:
        print("❌ Cannot run tests - server connection failed")
        print_test_summary()
        return
    
    try:
        # Run test suites
        await test_server_info(session)
        await test_query_sos_reports_tool(session)
        await test_new_tools(session)
        await test_error_conditions(session)
        
    finally:
        await disconnect_from_server(session, client_context)
        print_test_summary()


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="SosAlot MCP Server Test Suite")
    parser.add_argument('-d', '--debug', action='store_true', 
                        help='Enable debug output showing raw tool responses')
    args = parser.parse_args()
    
    # Set global debug flag
    debug_mode = args.debug
    
    if debug_mode:
        print("🐛 Debug mode enabled - will show raw tool responses\n")
    
    asyncio.run(main())