#!/usr/bin/env python3
"""
SosAlot Utilities

Shared utility functions and constants for the SosAlot MCP server.
"""

import os
import json
import time
from typing import Dict, List, Optional, Any

# Configuration - Use absolute path based on script location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOS_REPORTS_DIR = os.path.join(SCRIPT_DIR, "sos_reports")

# Data size limits for LLM efficiency
MAX_TEXT_SIZE = 10000      # Max characters for text content (logs, files)
MAX_LIST_ITEMS = 50        # Max items in lists (reports, errors, etc.)
MAX_LINE_COUNT = 500       # Max lines for log excerpts
MAX_RESPONSE_SIZE = 2 * 1024 * 1024  # Hard 2MB limit on JSON response


# =============================================================================
# CORE UTILITY FUNCTIONS
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
# SOS REPORT METADATA EXTRACTION FUNCTIONS
# =============================================================================

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
        return time.ctime(stat.st_mtime)
    except Exception:
        return None


# =============================================================================
# SIMPLIFIED REPORT ID AND SYMLINK MANAGEMENT
# =============================================================================

def sanitize_hostname(hostname: str) -> str:
    """Clean hostname for use in simplified IDs."""
    if not hostname:
        return "unknown"
    
    # Convert to lowercase, replace spaces and special chars with hyphens
    sanitized = hostname.lower().replace(' ', '-')
    # Keep only alphanumeric and hyphens
    sanitized = ''.join(c for c in sanitized if c.isalnum() or c == '-')
    # Remove multiple consecutive hyphens
    sanitized = '-'.join(filter(None, sanitized.split('-')))
    
    return sanitized or "unknown"


def parse_and_format_date(date_string: str) -> str:
    """Convert SOS report date to YYYYMMDD_HHMM format."""
    if not date_string:
        return "unknown"
    
    import re
    from datetime import datetime
    
    try:
        # Try to parse common date formats from SOS reports
        # Example: "Mon Dec  9 14:30:15 UTC 2025"
        # Example: "2025-12-09T14:30:15Z"
        
        # ISO format
        if 'T' in date_string and 'Z' in date_string:
            dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            return dt.strftime("%Y%m%d_%H%M")
        
        # Common Unix date format: "Mon Dec  9 14:30:15 UTC 2025"
        date_parts = date_string.strip().split()
        if len(date_parts) >= 5:
            try:
                # Extract components
                month_str = date_parts[1]
                day_str = date_parts[2]
                time_str = date_parts[3]
                year_str = date_parts[-1]  # Last part is usually year
                
                # Month name to number
                months = {
                    'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                    'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                    'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
                }
                
                month_num = months.get(month_str.lower()[:3], '01')
                day_num = day_str.zfill(2)
                year_num = year_str
                
                # Extract hour and minute from time (HH:MM:SS)
                time_parts = time_str.split(':')
                hour = time_parts[0].zfill(2) if len(time_parts) > 0 else '00'
                minute = time_parts[1].zfill(2) if len(time_parts) > 1 else '00'
                
                return f"{year_num}{month_num}{day_num}_{hour}{minute}"
            except (IndexError, ValueError):
                pass
        
        # Fallback: try to extract any date-like numbers
        numbers = re.findall(r'\d+', date_string)
        if len(numbers) >= 3:
            # Assume first 3 numbers are year, month, day or similar
            return f"{numbers[0]}{numbers[1].zfill(2)}{numbers[2].zfill(2)}_0000"
    
    except Exception:
        pass
    
    # Final fallback
    return "unknown"


def generate_report_id(report_path: str) -> str:
    """Generate a simplified, LLM-friendly report ID from SOS report metadata."""
    hostname = extract_hostname(report_path)
    creation_date = extract_creation_date(report_path)
    
    clean_hostname = sanitize_hostname(hostname)
    formatted_date = parse_and_format_date(creation_date)
    
    return f"{clean_hostname}_{formatted_date}"


def ensure_report_symlink(report_path: str) -> str:
    """Create symlink with simplified name, return the simplified ID.
    
    Falls back to original directory name if symlink creation fails
    (e.g., no write permissions or filesystem doesn't support symlinks like CIFS).
    """
    simplified_id = generate_report_id(report_path)
    symlink_path = os.path.join(SOS_REPORTS_DIR, simplified_id)
    
    # Only create if it doesn't already exist
    if not os.path.exists(symlink_path):
        try:
            # Get the directory name (not full path) for relative symlink
            target_dir = os.path.basename(report_path)
            os.symlink(target_dir, symlink_path)
        except OSError as e:
            # If symlink creation fails, just return the original directory name
            # This provides graceful fallback for read-only or unsupported filesystems
            print(f"[WARN] Could not create symlink for {simplified_id}: {e}")
            print(f"       Using full directory name instead. Check filesystem type and permissions.")
            return os.path.basename(report_path)
    
    return simplified_id


def resolve_report_path(report_id: str, internal_path: str = "") -> str:
    """Resolve simplified report ID to full internal path."""
    if internal_path:
        full_path = os.path.join(SOS_REPORTS_DIR, report_id, internal_path)
    else:
        full_path = os.path.join(SOS_REPORTS_DIR, report_id)
    
    return full_path


def validate_report_path_security(report_id: str, internal_path: str = "") -> Dict[str, Any]:
    """Validate that a report ID + path combination is safe and exists."""
    try:
        # Construct the path
        full_path = resolve_report_path(report_id, internal_path)
        
        # Convert to absolute path and resolve any symlinks/.. references
        abs_path = os.path.abspath(full_path)
        abs_sos_dir = os.path.abspath(SOS_REPORTS_DIR)
        
        # Check if path is within SOS_REPORTS_DIR
        if not abs_path.startswith(abs_sos_dir):
            return {
                "valid": False,
                "error": f"Path access denied: {report_id}/{internal_path} is outside allowed directory",
                "path": None
            }
        
        # Check if path exists
        if not os.path.exists(abs_path):
            return {
                "valid": False,
                "error": f"Path not found: {report_id}/{internal_path}",
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