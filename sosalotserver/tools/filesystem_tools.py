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


def list_dir(report: str, path: str = "", offset: int = 0, limit: int = 50, max_search: int = 500) -> Dict[str, Any]:
    """List contents of a directory within a SOS report with pagination.
    
    Args:
        report: Report ID from query_sos_reports (e.g., "centos9-original_20251209_1430")
        path: Path within the report (e.g., "etc", "var/log", "proc"). Use empty string for root.
        offset: Skip this many matching items (default: 0)
        limit: Return at most this many items (default: 50)
        max_search: Stop searching after finding this many total matches (default: 500)
        
    Returns:
        Dictionary with:
        - 'items': List of directory contents with type info  
        - 'total_items': Total number of items found
        - 'pagination': Pagination information
        
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
        
        # Apply limits for search budget (max_search controls how many we consider)
        max_search = min(max_search, 2000)  # Hard limit on items to process
        items_to_process = all_items[:max_search]
        items_found = len(items_to_process)
        
        # Apply pagination to processed items
        total_items = len(items_to_process)
        limit = min(limit, 100)  # Hard limit on page size
        start_idx = offset
        end_idx = offset + limit
        
        paginated_items = items_to_process[start_idx:end_idx]
        
        return {
            "items": paginated_items,
            "total_items": total_items,
            "pagination": {
                "offset": offset,
                "limit": limit,
                "returned": len(paginated_items),
                "has_more": end_idx < total_items
            }
        }
        
    except Exception as e:
        return {
            "error": f"Error reading directory: {str(e)}"
        }


def find_files_by_name(report: str, pattern: str, search_path: str = "", 
                      offset: int = 0, limit: int = 50, max_search: int = 500) -> Dict[str, Any]:
    """Find files by name pattern within a single directory (non-recursive).
    
    Searches ONLY in the specified directory, NOT in subdirectories.
    Pattern matching is CASE-INSENSITIVE and matches against FILENAME only (not full path).
    Supports pagination for large directories.
    
    Args:
        report: Report ID from query_sos_reports (e.g., "centos9-original_20251209_1430")
        pattern: Glob pattern to match filenames (e.g., "*swap*", "*.log", "*hostname*", "ip_*")
        search_path: Path within report to search (default: search report root directory)
        offset: Skip this many matching items (for pagination, default 0)
        limit: Return at most this many items (default 50, max 100)
        max_search: Stop searching after finding this many total matches (default 500, max 2000)
        
    Returns:
        Dictionary with search results and pagination info
        
    Search Behavior:
    - NON-RECURSIVE: Searches only the specified directory
    - CASE-INSENSITIVE: "Swap" matches "swap", "SWAP", "SwAp"
    - FILENAME ONLY: Pattern matches against filename, not full path
    - PAGINATED: Use offset/limit to browse large directories
    
    Common patterns:
    - "*swap*" - Find files containing "swap" in filename (case-insensitive)
    - "*hostname*" - Find hostname-related files
    - "*.conf" - Find configuration files  
    - "ip_*" - Find files starting with "ip_"
    
    Examples:
    - find_files_by_name("report1", "*.conf", "etc", limit=20) 
      → First 20 .conf files in etc/ directory only
    - find_files_by_name("report1", "*SWAP*", "sos_commands/memory")
      → Find swapon, swapoff files in memory directory only
    
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
        # Find matches in current directory only
        all_matches = []
        report_root = resolve_report_path(report, "")
        matches_found = 0
        
        # Limit search scope to prevent runaway searches
        max_search = min(max_search, 2000)
        
        if os.path.exists(search_root):
            items = os.listdir(search_root)
            
            for item in items:
                # Case-insensitive pattern matching
                import fnmatch
                if fnmatch.fnmatch(item.lower(), pattern.lower()):
                    full_path = os.path.join(search_root, item)
                    
                    try:
                        rel_path = os.path.relpath(full_path, report_root)
                    except ValueError:
                        continue
                    
                    # Determine item type
                    if os.path.islink(full_path):
                        item_type = "symlink"
                    elif os.path.isdir(full_path):
                        item_type = "dir"
                    else:
                        item_type = "file"
                    
                    all_matches.append({
                        "path": rel_path,
                        "type": item_type
                    })
                    
                    matches_found += 1
                    
                    # Stop if we've found too many matches
                    if matches_found >= max_search:
                        break
        
        # Sort matches for consistent output
        all_matches.sort(key=lambda x: (x["type"] != "dir", x["path"]))
        
        # Apply pagination
        total_matches = len(all_matches)
        limit = min(limit, 100)  # Hard limit on page size
        start_idx = offset
        end_idx = offset + limit
        
        paginated_matches = all_matches[start_idx:end_idx]
        
        return {
            "matches": paginated_matches,
            "total_matches": total_matches,
            "pagination": {
                "offset": offset,
                "limit": limit,
                "returned": len(paginated_matches),
                "has_more": end_idx < total_matches
            }
        }
        
    except Exception as e:
        return {
            "error": f"Search error: {str(e)}",
            "search_info": {"report": report, "pattern": pattern, "search_path": search_path}
        }


def find_files_by_name_recursive(report: str, pattern: str, search_path: str = "", 
                                offset: int = 0, limit: int = 50, max_search: int = 500) -> Dict[str, Any]:
    """Find files by name pattern recursively through all subdirectories.
    
    Searches RECURSIVELY through all subdirectories from the search_path.
    Pattern matching is CASE-INSENSITIVE and matches against FILENAME only (not full path).
    Supports pagination for large result sets.
    
    Args:
        report: Report ID from query_sos_reports (e.g., "centos9-original_20251209_1430")
        pattern: Glob pattern to match filenames (e.g., "*swap*", "*.log", "*hostname*", "ip_*")
        search_path: Path within report to start search (default: search entire report recursively)
        offset: Skip this many matching items (for pagination, default 0)
        limit: Return at most this many items (default 50, max 100)
        max_search: Stop searching after finding this many total matches (default 500, max 2000)
        
    Returns:
        Dictionary with search results and pagination info
        
    Search Behavior:
    - RECURSIVE: Searches all subdirectories under search_path
    - CASE-INSENSITIVE: "Swap" matches "swap", "SWAP", "SwAp"
    - FILENAME ONLY: Pattern matches against filename, not full path
    - PAGINATED: Use offset/limit to browse large result sets
    
    Common patterns:
    - "*swap*" - Find files containing "swap" in filename (case-insensitive)
    - "*hostname*" - Find hostname-related files  
    - "*.conf" - Find configuration files everywhere
    - "ip_*" - Find files starting with "ip_"
    - "*log*" - Find files containing "log" in filename
    
    Examples:
    - find_files_by_name_recursive("report1", "*swap*", "sos_commands") 
      → Finds sos_commands/memory/swapon_--summary_--verbose recursively
    - find_files_by_name_recursive("report1", "*.conf", "etc", offset=0, limit=20)
      → First 20 .conf files under etc/ and all subdirectories
    
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
        # Find matches recursively
        all_matches = []
        report_root = resolve_report_path(report, "")
        matches_found = 0
        
        # Limit search scope to prevent runaway searches
        max_search = min(max_search, 2000)
        
        # Walk through all directories from search_root
        for root, dirs, files in os.walk(search_root):
            # Check all items (files and directories) in this directory
            all_items = files + dirs
            
            for item in all_items:
                # Case-insensitive pattern matching
                import fnmatch
                if fnmatch.fnmatch(item.lower(), pattern.lower()):
                    full_path = os.path.join(root, item)
                    
                    try:
                        rel_path = os.path.relpath(full_path, report_root)
                    except ValueError:
                        continue
                    
                    # Determine item type
                    if os.path.islink(full_path):
                        item_type = "symlink"
                    elif os.path.isdir(full_path):
                        item_type = "dir"
                    else:
                        item_type = "file"
                    
                    all_matches.append({
                        "path": rel_path,
                        "type": item_type
                    })
                    
                    matches_found += 1
                    
                    # Stop if we've found too many matches
                    if matches_found >= max_search:
                        break
            
            # Break out of os.walk if we've found enough
            if matches_found >= max_search:
                break
        
        # Sort matches for consistent output
        all_matches.sort(key=lambda x: (x["type"] != "dir", x["path"]))
        
        # Apply pagination
        total_matches = len(all_matches)
        limit = min(limit, 100)  # Hard limit on page size
        start_idx = offset
        end_idx = offset + limit
        
        paginated_matches = all_matches[start_idx:end_idx]
        
        return {
            "matches": paginated_matches,
            "total_matches": total_matches,
            "pagination": {
                "offset": offset,
                "limit": limit,
                "returned": len(paginated_matches),
                "has_more": end_idx < total_matches
            }
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
            "error": f"Cannot access file: {str(e)}"
        }
    
    # Check if it's actually a file
    if not os.path.isfile(target_path):
        return {
            "error": f"Path is not a file: {path}"
        }
    
    # Read file content safely
    file_content = read_file_safely(target_path)
    if file_content is None:
        return {
            "error": f"Unable to read file: {path}"
        }
    
    # Apply character-based pagination
    total_size = len(file_content)
    
    # Handle offset bounds
    if offset >= total_size:
        return {
            "content": "",
            "total_size": total_size,
            "pagination": {
                "offset": offset,
                "limit": limit,
                "returned": 0,
                "has_more": false
            }
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
        "total_size": total_size,
        "pagination": {
            "offset": offset,
            "limit": limit,
            "returned": returned,
            "has_more": not eof
        }
    }


def search_file(report: str, path: str, substring: str, lines_before: int = 0, lines_after: int = 0, 
               offset: int = 0, limit: int = 10000, max_matches: int = 50) -> Dict[str, Any]:
    """Search for text within a specific file from a SOS report with character-based output limiting.
    
    Args:
        report: Report ID from query_sos_reports (e.g., "centos9-original_20251209_1430")
        path: Path to file within report (e.g., "sos_commands/networking/ip_addr")
        substring: Text to search for (case-insensitive)
        lines_before: Context lines before each match (default: 0)
        lines_after: Context lines after each match (default: 0)
        offset: Character position to start output from (default: 0)
        limit: Maximum characters to return (default: 10000)
        max_matches: Maximum matches to return (default 50, max 200)
    
    Returns:
        Dictionary with search results and character-based pagination info
        
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
    
    # Apply match limits
    max_matches = min(max_matches, 200)  # Hard limit on matches
    limited_matches = all_matches[:max_matches]
    total_matches = len(limited_matches)
    
    # Generate output text from matches
    output_lines = []
    for match in limited_matches:
        output_lines.append(f"=== Match at line {match['match_line']} ===")
        for ctx in match["context"]:
            prefix = ">>> " if ctx["is_match"] else "    "
            output_lines.append(f"{prefix}{ctx['line_number']:4d}: {ctx['content']}")
        output_lines.append("")  # Empty line between matches
    
    full_output = "\n".join(output_lines)
    
    # Apply character-based pagination 
    limit = min(limit, 50000)  # Hard limit on character output
    start_pos = offset
    end_pos = offset + limit
    
    output_slice = full_output[start_pos:end_pos]
    total_output_size = len(full_output)
    
    return {
        "matches": limited_matches,
        "output": output_slice,
        "total_matches": total_matches,
        "pagination": {
            "offset": offset,
            "limit": limit,
            "returned": len(output_slice),
            "total_size": total_output_size,
            "has_more": end_pos < total_output_size
        }
    }