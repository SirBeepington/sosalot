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
import os
import json
import glob
from pathlib import Path
from typing import Dict, List, Optional, Any

# Import all utilities from utils module
from utils import *

# Create the SosAlot MCP server
sosalot = FastMCP("SosAlot", json_response=True)


# =============================================================================
# IMPORT AND REGISTER TOOLS FROM MODULES
# =============================================================================

def read_file_safely(file_path: str) -> Optional[str]:
    """Safely read a file and return its content."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception:
        return None


def truncate_text(text: str, max_size: int = MAX_TEXT_SIZE) -> Dict[str, Any]:
    """Truncate text to max size and return with metadata."""
    if not text:
        return {"content": None, "truncated": False, "original_size": 0}
    
    original_size = len(text)
    if original_size <= max_size:
        return {"content": text, "truncated": False, "original_size": original_size}
    
    # Truncate and add indicator
    truncated_text = text[:max_size]
    return {
        "content": truncated_text,
        "truncated": True,
        "original_size": original_size,
        "showing_size": max_size
    }


def limit_list(items: List, max_items: int = MAX_LIST_ITEMS) -> Dict[str, Any]:
    """Limit list size and return with metadata."""
    if not items:
        return {"items": [], "truncated": False, "total_count": 0}
    
    total_count = len(items)
    if total_count <= max_items:
        return {"items": items, "truncated": False, "total_count": total_count}
    
    limited_items = items[:max_items]
    return {
        "items": limited_items,
        "truncated": True,
        "total_count": total_count,
        "showing_count": max_items
    }


def enforce_response_size_limit(response_data: Any) -> Any:
    """Hard 2MB backstop - truncate response if it exceeds MAX_RESPONSE_SIZE."""
    import json
    
    # Serialize to JSON to check size
    json_response = json.dumps(response_data, indent=None, separators=(',', ':'))
    response_size = len(json_response.encode('utf-8'))
    
    if response_size <= MAX_RESPONSE_SIZE:
        return response_data
    
    # Hard truncation - cut the JSON string and append warning
    max_chars = MAX_RESPONSE_SIZE - 100  # Reserve space for truncation message
    truncated_json = json_response[:max_chars]
    
    # Find last complete field to avoid broken JSON
    last_comma = truncated_json.rfind(',')
    if last_comma > 0:
        truncated_json = truncated_json[:last_comma]
    
    # Close JSON properly and add truncation notice
    truncation_msg = f'"_truncation_warning": "Max response size of {MAX_RESPONSE_SIZE//1024//1024}MB reached, truncating response"'
    
    # Remove trailing comma/brace and reconstruct
    if truncated_json.endswith('}'):
        truncated_json = truncated_json[:-1] + ',' + truncation_msg + '}'
    elif truncated_json.endswith(','):
        truncated_json = truncated_json + truncation_msg + '}'
    else:
        truncated_json = '{' + truncation_msg + '}'
    
    try:
        return json.loads(truncated_json)
    except json.JSONDecodeError:
        # Fallback: return minimal error response
        return {
            "error": "Response too large",
            "_truncation_warning": f"Max response size of {MAX_RESPONSE_SIZE//1024//1024}MB reached, truncating response",
            "original_size_mb": response_size / 1024 / 1024
        }


def extract_hostname(report_path: str) -> Optional[str]:
    """Extract hostname from SOS report."""
    # Primary: ./etc/hostname (as per dev_notes.md)
    hostname_file = os.path.join(report_path, "etc", "hostname")
    content = read_file_safely(hostname_file)
    if content:
        return content.strip()
    
    # Fallback: direct hostname file (for compatibility)
    hostname_file = os.path.join(report_path, "hostname")
    content = read_file_safely(hostname_file)
    if content:
        return content.strip()
    
    # Fallback: sos_commands/general/hostname
    hostname_file = os.path.join(report_path, "sos_commands", "general", "hostname")
    content = read_file_safely(hostname_file)
    return content.strip() if content else None


def extract_serial_number(report_path: str) -> Optional[str]:
    """Extract serial number from dmidecode output."""
    # Primary: ./sos_commands/hardware/dmidecode (as per dev_notes.md)
    dmidecode_file = os.path.join(report_path, "sos_commands", "hardware", "dmidecode")
    content = read_file_safely(dmidecode_file)
    
    if not content:
        # Fallback: direct dmidecode file (for compatibility)
        dmidecode_file = os.path.join(report_path, "dmidecode")
        content = read_file_safely(dmidecode_file)
    
    if not content:
        return None
    
    # Parse "System Information" -> "Serial Number:" line
    lines = content.split('\n')
    in_system_info = False
    
    for line in lines:
        if "System Information" in line:
            in_system_info = True
        elif in_system_info and "Serial Number:" in line:
            # Extract serial number after "Serial Number:"
            serial = line.split("Serial Number:", 1)[-1].strip()
            return serial if serial != "Not Specified" else None
        elif in_system_info and line.strip() == "":
            # Empty line might indicate end of section
            continue
        elif in_system_info and not line.startswith('\t') and not line.startswith(' '):
            # New section started, stop looking
            break
    
    return None


def extract_uuid(report_path: str) -> Optional[str]:
    """Extract UUID from dmidecode output."""
    # Primary: ./sos_commands/hardware/dmidecode (as per dev_notes.md)
    dmidecode_file = os.path.join(report_path, "sos_commands", "hardware", "dmidecode")
    content = read_file_safely(dmidecode_file)
    
    if not content:
        # Fallback: direct dmidecode file (for compatibility)
        dmidecode_file = os.path.join(report_path, "dmidecode")
        content = read_file_safely(dmidecode_file)
    
    if not content:
        return None
    
    # Parse "System Information" -> "UUID:" line
    lines = content.split('\n')
    in_system_info = False
    
    for line in lines:
        if "System Information" in line:
            in_system_info = True
        elif in_system_info and "UUID:" in line:
            # Extract UUID after "UUID:"
            uuid = line.split("UUID:", 1)[-1].strip()
            return uuid if uuid != "Not Specified" else None
        elif in_system_info and line.strip() == "":
            # Empty line might indicate end of section
            continue
        elif in_system_info and not line.startswith('\t') and not line.startswith(' '):
            # New section started, stop looking
            break
    
    return None


def extract_creation_date(report_path: str) -> Optional[str]:
    """Extract SOS report creation date with fallbacks."""
    # Primary: ./sos_commands/date/date_--utc (as per dev_notes.md)
    date_file = os.path.join(report_path, "sos_commands", "date", "date_--utc")
    date_content = read_file_safely(date_file)
    if date_content:
        return date_content.strip()
    
    # Fallback 1: manifest.json
    manifest_file = os.path.join(report_path, "manifest.json")
    manifest_content = read_file_safely(manifest_file)
    
    if manifest_content:
        try:
            manifest_data = json.loads(manifest_content)
            # Look for start timestamp
            if "start" in manifest_data:
                return manifest_data["start"]
        except json.JSONDecodeError:
            pass
    
    # Fallback 2: direct date file (for compatibility)
    date_file = os.path.join(report_path, "date")
    date_content = read_file_safely(date_file)
    if date_content:
        # Parse the date output - extract the "Local time:" line
        lines = date_content.split('\n')
        for line in lines:
            if "Local time:" in line:
                # Extract time after "Local time:"
                date_part = line.split("Local time:", 1)[-1].strip()
                return date_part
        # If no "Local time:" found, return first non-empty line
        for line in lines:
            if line.strip():
                return line.strip()
    
    # Fallback 3: sos_commands/general/date
    date_file = os.path.join(report_path, "sos_commands", "general", "date")
    date_content = read_file_safely(date_file)
    if date_content:
        return date_content.strip()
    
    # Fallback 4: directory timestamp
    try:
        stat = os.path.stat(report_path)
        import time
        return time.ctime(stat.st_mtime)
    except Exception:
        return None



def validate_path_security(path: str) -> Dict[str, Any]:
    """Validate that a path is safe and within allowed directories."""
    try:
        # Convert to absolute path and resolve any symlinks/.. references
        abs_path = os.path.abspath(path)
        abs_sos_dir = os.path.abspath(SOS_REPORTS_DIR)
        
        # Check if path is within SOS_REPORTS_DIR
        if not abs_path.startswith(abs_sos_dir):
            return {
                "valid": False,
                "error": f"Path access denied: {path} is outside allowed directory",
                "path": None
            }
        
        # Check if path exists
        if not os.path.exists(abs_path):
            return {
                "valid": False,
                "error": f"Path not found: {path}",
                "path": None
            }
        
        return {
            "valid": True,
            "error": None,
            "path": abs_path
        }
    
    except Exception as e:
        return {
            "valid": False,
            "error": f"Path validation error: {str(e)}",
            "path": None
        }


def paginate_text_data(data: str, offset: int = 0, limit: int = MAX_TEXT_SIZE) -> Dict[str, Any]:
    """Paginate text data using character-based offsets."""
    if not data:
        return {
            "offset": offset,
            "returned": 0,
            "next_offset": None,
            "eof": True,
            "total_size": 0,
            "content": ""
        }
    
    total_size = len(data)
    
    # Handle offset beyond data
    if offset >= total_size:
        return {
            "offset": offset,
            "returned": 0,
            "next_offset": None,
            "eof": True,
            "total_size": total_size,
            "content": ""
        }
    
    # Extract the requested chunk
    end_pos = min(offset + limit, total_size)
    content = data[offset:end_pos]
    returned_chars = len(content)
    
    # Determine if we've reached end of data
    eof = end_pos >= total_size
    next_offset = end_pos if not eof else None
    
    return {
        "offset": offset,
        "returned": returned_chars,
        "next_offset": next_offset,
        "eof": eof,
        "total_size": total_size,
        "content": content
    }


# =============================================================================
# IMPORT AND REGISTER TOOLS FROM MODULES
# =============================================================================

# Import tools from modules
from report_discovery import query_sos_reports
from filesystem_tools import list_dir, search_for_files_and_directories, read_file, search_file

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

## Workflow for Analyzing SOS Reports:

1. **Start with query_sos_reports()** - Get available reports and their report_path
2. **Use list_dir(report_path)** - Explore the top-level structure
3. **Navigate to specific areas** using list_dir() or search_for_files_and_directories()
4. **Read files** with read_file() or search within files with search_file()

## Common Directory Structure:

```
{report_path}/
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
- File: `{report_path}/sos_commands/networking/ip_addr`
- Search for: "inet " (note the space)
- Example: read_file("{report_path}/sos_commands/networking/ip_addr")

### Hostname:
- File: `{report_path}/etc/hostname`
- Already extracted in query_sos_reports results

### Hardware Info:
- File: `{report_path}/sos_commands/hardware/dmidecode`
- Search for: "Serial Number", "Product Name", "Manufacturer"

### Running Services:
- File: `{report_path}/sos_commands/system/systemctl_list-units`
- Search for: "active", "failed"

### System Errors:
- Files: `{report_path}/var/log/messages`
- Search for: "error", "ERROR", "failed", "FAILED"

### Network Configuration:
- Directory: `{report_path}/sos_commands/networking/`
- Files: ip_addr, ip_route, netstat, etc.

## Example Queries:

1. Get reports: `query_sos_reports()`
2. List top level: `list_dir("{report_path}")`
3. Find IP addresses: `read_file("{report_path}/sos_commands/networking/ip_addr")`
4. Search for errors: `search_file("{report_path}/var/log/messages", "error", 2, 2)`

## Important Notes:

- Always use the full report_path from query_sos_reports()
- File paths are case-sensitive
- Some files may not exist in all reports
- Use search_for_files_and_directories() if unsure about file locations
"""


# Run with streamable HTTP transport
if __name__ == "__main__":
    sosalot.run(transport="streamable-http")
if __name__ == "__main__":
    sosalot.run(transport="streamable-http")