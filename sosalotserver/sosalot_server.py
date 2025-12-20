#!/usr/bin/env python3
"""
SosAlot - SOS Report Analysis MCP Server

A Model Context Protocol server for analyzing Linux SOS reports.

Usage:
    python sosalot_server.py
"""

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
# IMPORT AND REGISTER TOOLS FROM MODULES
# =============================================================================

# Import tools from modules
from tools.report_discovery import query_sos_reports
from tools.filesystem_tools import list_dir, search_for_files_and_directories, read_file, search_file

# Register all tools with the MCP server
sosalot.tool()(query_sos_reports)
sosalot.tool()(list_dir)
sosalot.tool()(search_for_files_and_directories)
sosalot.tool()(read_file)
sosalot.tool()(search_file)


# =============================================================================
# MCP RESOURCES - Help LLMs understand SOS report structure
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


# Run with streamable HTTP transport
if __name__ == "__main__":
    sosalot.run(transport="streamable-http")