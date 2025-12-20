#!/usr/bin/env python3
"""
SosAlot Filesystem Tools

Tools for listing, searching, and reading files within SOS reports.
Uses simplified report IDs to hide complex directory names from LLM clients.
"""

import os
import json
import glob as glob_module
from typing import Dict, Optional, Any, List

from utils import (
    MAX_TEXT_SIZE,
    resolve_report_path,
    validate_report_path_security,
    read_file_safely,
    limit_list,
    enforce_response_size_limit
)


def list_dir(report: str, path: str = "", max_items: int = 50) -> Dict[str, Any]:
    """List contents of a directory within a SOS report.
    
    Args:
        report: Report ID from query_sos_reports (e.g., "centos9-original_20251209_1430")
        path: Path within the report (e.g., "etc", "var/log", "proc"). Use empty string for root.
        max_items: Maximum items to return (default 50, max 200)
        
    Returns:
        Dictionary with:
        - 'items': List of directory contents with type info
        - 'path_info': Current path information
        - 'truncated': Boolean if results were limited
        
    Note: Directories end with '/' in the name field.
    
    Common useful paths:
    - "etc" - Configuration files (hostname, os-release, etc.)
    - "var/log" - Log files
    - "sos_commands" - Command outputs organized by category
    - "proc" - Process and system information
    """
    # Resolve report ID to actual path and validate
    try:
        target_path = resolve_report_path(report, path)
        validation = validate_report_path_security(report, path)
        if not validation["valid"]:
            return {
                "error": validation["error"],
                "path_info": {"report": report, "path": path}
            }
        target_path = validation["path"]
    except Exception as e:
        return {
            "error": f"Cannot access path: {str(e)}",
            "path_info": {"report": report, "path": path}
        }
    
    # Check if it's actually a directory
    if not os.path.isdir(target_path):
        return {
            "error": "Not a directory",
            "path_info": {"report": report, "path": path, "resolved_path": target_path}
        }

    try:
        # Get directory entries
        all_items = []
        for item in os.listdir(target_path):
            item_path = os.path.join(target_path, item)
            
            # Determine item type and format name
            if os.path.islink(item_path):
                item_type = "symlink"
                name = item + " -> " + os.readlink(item_path)
            elif os.path.isdir(item_path):
                item_type = "dir"
                name = item + "/"
            else:
                item_type = "file"
                name = item
            
            all_items.append({
                "name": name,
                "type": item_type,
                "raw_name": item
            })
        
        # Sort for consistent output: directories first, then files, alphabetically
        all_items.sort(key=lambda x: (x["type"] != "dir", x["raw_name"]))
        
        # Apply limits and prepare response
        max_items = min(max_items, 200)  # Hard limit
        limit_result = limit_list(all_items, max_items)
        limited_items = limit_result["items"]
        total_items = limit_result["total_count"]
        
        return {
            "items": limited_items,
            "path_info": {
                "report": report,
                "path": path,
                "resolved_path": target_path,
                "total_items": total_items
            },
            "truncated": limit_result["truncated"]
        }
        
    except Exception as e:
        return {
            "error": f"Error reading directory: {str(e)}",
            "path_info": {"report": report, "path": path}
        }


def search_for_files_and_directories(report: str, pattern: str, search_path: str = "", max_results: int = 100) -> Dict[str, Any]:
    """Search for files and directories using glob patterns within a SOS report.
    
    Args:
        report: Report ID from query_sos_reports (e.g., "centos9-original_20251209_1430")
        pattern: Glob pattern (e.g., "*.log", "*hostname*", "ip_*")
        search_path: Path within report to search (default: search entire report)
        max_results: Maximum results to return (default 100, max 500)
        
    Returns:
        Dictionary with search results
        
    Common patterns:
    - "*hostname*" - Find hostname-related files
    - "*.conf" - Find configuration files  
    - "ip_*" - Find IP-related command outputs
    - "*log*" - Find log files
    
    Security: Globstar (**) patterns are not allowed.
    """
    # Validate pattern
    if "**" in pattern:
        return {
            "error": "Globstar (**) patterns are not supported for security reasons",
            "pattern": pattern,
            "search_info": {"report": report, "search_path": search_path}
        }
    
    # Resolve search root and validate
    try:
        search_root = resolve_report_path(report, search_path)
        validation = validate_report_path_security(report, search_path)
        if not validation["valid"]:
            return {
                "error": validation["error"],
                "search_info": {"report": report, "search_path": search_path}
            }
        search_root = validation["path"]
    except Exception as e:
        return {
            "error": f"Cannot access search path: {str(e)}",
            "search_info": {"report": report, "search_path": search_path}
        }
    
    try:
        # Build search pattern
        search_pattern = os.path.join(search_root, pattern)
        
        # Find matches
        all_matches = []
        for match_path in glob_module.glob(search_pattern):
            # Get path relative to report root for clean display
            report_root = resolve_report_path(report, "")
            try:
                rel_path = os.path.relpath(match_path, report_root)
            except ValueError:
                continue  # Skip if path cannot be made relative
                
            # Determine item type
            if os.path.islink(match_path):
                item_type = "symlink"
            elif os.path.isdir(match_path):
                item_type = "dir"
            else:
                item_type = "file"
            
            all_matches.append({
                "path": rel_path,
                "type": item_type
            })
        
        # Sort matches for consistent output
        all_matches.sort(key=lambda x: (x["type"] != "dir", x["path"]))
        
        # Apply limits
        max_results = min(max_results, 500)  # Hard limit
        limit_result = limit_list(all_matches, max_results)
        limited_matches = limit_result["items"]
        total_matches = limit_result["total_count"]
        
        return {
            "matches": limited_matches,
            "search_info": {
                "report": report,
                "pattern": pattern,
                "search_path": search_path,
                "total_matches": total_matches
            },
            "truncated": limit_result["truncated"]
        }
        
    except Exception as e:
        return {
            "error": f"Search error: {str(e)}",
            "search_info": {"report": report, "pattern": pattern, "search_path": search_path}
        }
def read_file(report: str, path: str, offset: int = 0, limit: int = MAX_TEXT_SIZE) -> Dict[str, Any]:
    """Read the contents of a file from a SOS report with pagination.
    
    Args:
        report: Report ID from query_sos_reports (e.g., "centos9-original_20251209_1430")
        path: Path to file within report (e.g., "etc/hostname", "var/log/messages")
        offset: Character offset to start reading (use 0 for beginning)
        limit: Maximum characters to return
    
    Returns:
        Dictionary with file content and pagination info
        
    Common useful files:
    - "etc/hostname" - System hostname
    - "etc/os-release" - OS version info
    - "sos_commands/networking/ip_addr" - IP addresses
    - "sos_commands/networking/ip_route" - Routing table
    - "sos_commands/hardware/dmidecode" - Hardware info
    - "var/log/messages" - System log messages
    """
    # Resolve and validate path
    try:
        target_path = resolve_report_path(report, path)
        validation = validate_report_path_security(report, path)
        if not validation["valid"]:
            return {
                "error": validation["error"],
                "file_info": {"report": report, "path": path},
                "offset": offset,
                "eof": True
            }
        target_path = validation["path"]
    except Exception as e:
        return {
            "error": f"Cannot access file: {str(e)}",
            "file_info": {"report": report, "path": path},
            "offset": offset,
            "eof": True
        }
    
    # Check if it's actually a file
    if not os.path.isfile(target_path):
        return {
            "error": f"Path is not a file: {path}",
            "file_info": {"report": report, "path": path},
            "offset": offset,
            "eof": True
        }
    
    # Read file content safely
    file_content = read_file_safely(target_path)
    if file_content is None:
        return {
            "error": f"Unable to read file: {path}",
            "file_info": {"report": report, "path": path},
            "offset": offset,
            "eof": True
        }
    
    # Apply character-based pagination
    total_size = len(file_content)
    
    # Handle offset bounds
    if offset >= total_size:
        return {
            "content": "",
            "file_info": {"report": report, "path": path, "total_size": total_size},
            "offset": offset,
            "returned": 0,
            "eof": True,
            "next_offset": None
        }
    
    # Extract the requested slice
    end_pos = offset + limit
    content_slice = file_content[offset:end_pos]
    
    # Calculate pagination info
    returned = len(content_slice)
    eof = (offset + returned >= total_size)
    next_offset = None if eof else offset + returned
    
    return {
        "content": content_slice,
        "file_info": {"report": report, "path": path, "total_size": total_size},
        "offset": offset,
        "returned": returned,
        "eof": eof,
        "next_offset": next_offset
    }


def search_file(report: str, path: str, substring: str, lines_before: int = 0, lines_after: int = 0, max_matches: int = 50) -> Dict[str, Any]:
    """Search for text within a specific file from a SOS report.
    
    Args:
        report: Report ID from query_sos_reports (e.g., "centos9-original_20251209_1430")
        path: Path to file within report (e.g., "sos_commands/networking/ip_addr")
        substring: Text to search for (case-insensitive)
        lines_before: Context lines before each match (default: 0)
        lines_after: Context lines after each match (default: 0)
        max_matches: Maximum matches to return (default 50, max 200)
    
    Returns:
        Dictionary with search results
        
    Tips:
    - Search for "inet " in networking files to find IP addresses
    - Search for "ERROR" or "error" in log files
    - Search for "=" in config files to find settings
    """
    # Resolve and validate path
    try:
        target_path = resolve_report_path(report, path)
        validation = validate_report_path_security(report, path)
        if not validation["valid"]:
            return {
                "error": validation["error"],
                "search_info": {"report": report, "path": path, "substring": substring}
            }
        target_path = validation["path"]
    except Exception as e:
        return {
            "error": f"Cannot access file: {str(e)}",
            "search_info": {"report": report, "path": path, "substring": substring}
        }
    
    # Check if it's actually a file
    if not os.path.isfile(target_path):
        return {
            "error": f"Path is not a file: {path}",
            "search_info": {"report": report, "path": path, "substring": substring}
        }
    
    # Read file content safely
    file_content = read_file_safely(target_path)
    if file_content is None:
        return {
            "error": f"Unable to read file: {path}",
            "search_info": {"report": report, "path": path, "substring": substring}
        }
    
    # Split into lines for searching
    lines = file_content.split('\n')
    all_matches = []
    
    # Search for substring in each line
    for line_num, line in enumerate(lines):
        if substring.lower() in line.lower():  # Case-insensitive search
            # Calculate context range
            start_line = max(0, line_num - lines_before)
            end_line = min(len(lines), line_num + lines_after + 1)
            
            # Extract context lines
            context_lines = []
            for ctx_line_num in range(start_line, end_line):
                context_lines.append({
                    "line_number": ctx_line_num + 1,  # 1-based line numbers
                    "content": lines[ctx_line_num],
                    "is_match": ctx_line_num == line_num
                })
            
            all_matches.append({
                "match_line": line_num + 1,  # 1-based line numbers
                "match_content": line,
                "context": context_lines
            })
    
    # Apply limits
    max_matches = min(max_matches, 200)  # Hard limit
    limit_result = limit_list(all_matches, max_matches)
    limited_matches = limit_result["items"]
    total_matches = limit_result["total_count"]
    
    return {
        "matches": limited_matches,
        "search_info": {
            "report": report,
            "path": path,
            "substring": substring,
            "total_matches": total_matches,
            "lines_before": lines_before,
            "lines_after": lines_after
        },
        "truncated": limit_result["truncated"]
    }