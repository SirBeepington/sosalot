#!/usr/bin/env python3
"""
SosAlot - SOS Report Analysis MCP Server

A Model Context Protocol server for analyzing Linux SOS reports.

Usage:
    python sosalot_server.py [-t strm|stdio] [--transport strm|stdio] [--reports-dir PATH]
    
Transport options:
    strm    - Use streamable HTTP (default)
    stdio   - Use stdio transport

Reports directory:
    --reports-dir PATH   - Directory containing SOS report directories (default: ./sos_reports)
    
Requirements:
    - Write access to reports directory (for creating simplified symlinks)
    - Filesystem must support symlinks (not CIFS/SMB shares)
    - Server will work without write access but will use full report directory names
"""

import argparse
import os
import json

# TODO: Future Tools to Add

# get_directory_map(root_path)
#   Return a small, fixed overview of key sosreport directories (not pageable).
#   Proposed implementation: Use manifest.json to provide intelligent directory structure
#   overview based on what sosreport actually collected for this specific report.
#   This will give LLMs a useful roadmap of available data sources.

from mcp.server.fastmcp import FastMCP

# Import all utilities from utils module
from utils import *

# Create the SosAlot MCP server
sosalot = FastMCP("SosAlot", json_response=True)


# =============================================================================
# LOAD TOOL DEFINITIONS FROM CONFIG
# =============================================================================

# Load optional tool definition overrides from JSON
TOOL_DEFS = {}
config_path = os.path.join(os.path.dirname(__file__), 'config', 'tool_definitions.json')
try:
    with open(config_path) as f:
        TOOL_DEFS = json.load(f).get('tools', {})
    print(f"[INFO] Loaded tool definitions from {config_path}")
except FileNotFoundError:
    print(f"[WARN] tool_definitions.json not found at {config_path}, using docstrings")
except json.JSONDecodeError as e:
    print(f"[WARN] Invalid JSON in tool_definitions.json: {e}")


def register_tool(func):
    """Register a tool with MCP, using JSON definition if available, otherwise use docstring."""
    tool_name = func.__name__
    
    # Override docstring if definition exists in JSON
    if tool_name in TOOL_DEFS and 'description' in TOOL_DEFS[tool_name]:
        func.__doc__ = TOOL_DEFS[tool_name]['description']
        print(f"  {tool_name}: using JSON definition")
    else:
        print(f"  {tool_name}: using docstring")
    
    sosalot.tool()(func)


# =============================================================================
# IMPORT AND REGISTER TOOLS FROM MODULES
# =============================================================================

# Import tools from modules
from tools.report_discovery import query_sos_reports
from tools.filesystem_tools import list_dir, find_files_by_name, find_files_by_name_recursive, read_file, search_file
from tools.info_sources_tool import get_info_sources_for_domain

# Register all tools with the MCP server
print("\nRegistering tools:")
register_tool(query_sos_reports)
register_tool(list_dir)
register_tool(find_files_by_name)
register_tool(find_files_by_name_recursive)
register_tool(read_file)
register_tool(search_file)
register_tool(get_info_sources_for_domain)
print("")


# =============================================================================
# MCP RESOURCES - Help LLMs understand SOS report structure
# =============================================================================

# =============================================================================
# MCP RESOURCES - Help LLMs understand SOS report structure
# =============================================================================

# =============================================================================
# MCP RESOURCES - Static content for reference (not model-discoverable)
# =============================================================================

@sosalot.resource("sos://report-guide")
def sos_report_structure_guide():
    """Guide to SOS report structure and common file locations."""
    return """
# SOS Report Structure Guide

SOS reports contain Linux system diagnostic information organized in a standard directory structure.

## NEW SIMPLIFIED API:

This server now uses simplified report IDs to make analysis easier for LLMs. 

### Workflow for Analyzing SOS Reports:

1. **Start with query_sos_reports()** - Get available reports and their simplified report_id
2. **Use list_dir(report="<report_id>")** - Explore the top-level structure
3. **Navigate to specific areas** using list_dir(report="<report_id>", path="<subdir>")
4. **Read files** with read_file(report="<report_id>", path="<file_path>")
5. **Search within files** with search_file(report="<report_id>", path="<file_path>", substring="<text>")

Example report_id: "centos9-original_20251209_1430"

## Common Directory Structure:

```
<report_id>/
├── etc/                    # System configuration files
│   ├── hostname           # System hostname  
│   ├── os-release         # OS version information
│   ├── fstab             # Filesystem table
│   ├── hosts             # Host file
│   └── passwd            # User accounts (passwords removed)
├── sos_commands/          # Output of diagnostic commands
│   ├── networking/       # Network-related commands
│   │   ├── ip_addr       # IP address information
│   │   ├── ip_route      # Routing table
│   │   └── netstat       # Network connections
│   ├── hardware/         # Hardware information
│   │   └── dmidecode     # Hardware details (serial numbers, etc.)
│   ├── system/           # System information
│   │   ├── ps            # Running processes
│   │   └── systemctl     # Service status
│   └── logs/             # Log file excerpts
├── var/log/               # System log files
│   ├── messages          # General system messages
│   ├── secure            # Security/auth logs
│   └── dmesg             # Kernel messages
├── proc/                  # Process and system info
│   ├── cpuinfo           # CPU information
│   ├── meminfo           # Memory information
│   └── mounts            # Mounted filesystems
└── version.txt            # SOS report version info
```

## Finding Specific Information:

### IP Addresses:
- Command: read_file(report="<report_id>", path="sos_commands/networking/ip_addr")
- Search for: "inet " (note the space)

### Hostname:
- Command: read_file(report="<report_id>", path="etc/hostname")
- Already extracted in query_sos_reports results

### Hardware Info:
- Command: read_file(report="<report_id>", path="sos_commands/hardware/dmidecode")
- Search for: "Serial Number", "Product Name", "Manufacturer"

### Running Services:
- Command: read_file(report="<report_id>", path="sos_commands/system/systemctl_list-units")
- Search for: "active", "failed"

### System Errors:
- Command: search_file(report="<report_id>", path="var/log/messages", substring="error")
- Search for: "error", "ERROR", "failed", "FAILED"

### Network Configuration:
- Command: list_dir(report="<report_id>", path="sos_commands/networking")
- Files: ip_addr, ip_route, netstat, etc.

## Example API Usage:

1. Get reports: query_sos_reports()
2. List top level: list_dir(report="centos9-original_20251209_1430")
3. Find IP addresses: read_file(report="centos9-original_20251209_1430", path="sos_commands/networking/ip_addr")
4. Search for errors: search_file(report="centos9-original_20251209_1430", path="var/log/messages", substring="error", lines_before=2, lines_after=2)

## Important Notes:

- Use the simplified report_id from query_sos_reports()
- File paths within reports do NOT need leading slash or report prefix
- Some files may not exist in all reports  
- Use search_for_files_and_directories() if unsure about file locations
- All tools now use clean report+path API instead of complex directory paths
"""


# Run with configurable transport
if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="SosAlot - SOS Report Analysis MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-t", "--transport", 
        choices=["strm", "stdio"],
        default="strm",
        help="Transport method: 'strm' for streamable HTTP (default), 'stdio' for stdio transport"
    )
    parser.add_argument(
        "--reports-dir",
        default="./sos_reports",
        help="Directory containing SOS report directories (default: ./sos_reports). "
             "This should point to a parent directory that contains one or more SOS report root directories, "
             "not to an individual SOS report directory itself. "
             "Requires write access and symlink support (not CIFS/SMB shares). "
             "Server will work without write access but will use full directory names."
    )
    
    args = parser.parse_args()
    
    # Configure SOS reports directory before importing tools
    import utils
    utils.SOS_REPORTS_DIR = os.path.abspath(args.reports_dir)
    print(f"[INFO] Using SOS reports directory: {utils.SOS_REPORTS_DIR}")
    
    # Check write access and symlink support
    if not os.path.exists(utils.SOS_REPORTS_DIR):
        print(f"[WARN] Reports directory does not exist: {utils.SOS_REPORTS_DIR}")
    elif not os.access(utils.SOS_REPORTS_DIR, os.W_OK):
        print(f"[WARN] No write access to reports directory. Symlink creation will fail.")
        print(f"       Server will still work but report IDs will use full directory names.")
    
    # Map transport argument to actual transport string
    transport_map = {
        "strm": "streamable-http",
        "stdio": "stdio"
    }
    
    transport = transport_map[args.transport]
    print(f"[INFO] Starting SosAlot MCP server with '{transport}' transport")
    
    if transport == "stdio":
        print("[INFO] Server will communicate via stdin/stdout (no HTTP server)")
    else:
        print("[INFO] Server will start HTTP server on http://127.0.0.1:8000")
    
    sosalot.run(transport=transport)