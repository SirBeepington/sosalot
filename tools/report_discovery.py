#!/usr/bin/env python3
"""
SosAlot Report Discovery Tools

Tools for discovering and querying available SOS reports.
"""

import os
import json
from typing import Dict, List, Optional, Any

from utils import (
    SOS_REPORTS_DIR,
    REPORT_CACHE_FILENAME,
    REFRESH_REPORT_CACHE,
    extract_hostname,
    extract_serial_number,
    extract_uuid,
    extract_creation_date,
    generate_report_id,
    limit_list,
    enforce_response_size_limit
)


def _get_cache_path() -> str:
    """Return the full path to the report metadata cache file."""
    return os.path.join(SOS_REPORTS_DIR, REPORT_CACHE_FILENAME)


def _load_report_cache() -> Dict[str, Any]:
    """Load cached report metadata if available, otherwise return empty cache."""
    cache_path = _get_cache_path()
    if REFRESH_REPORT_CACHE and os.path.exists(cache_path):
        try:
            os.remove(cache_path)
        except OSError:
            pass

    if not os.path.exists(cache_path):
        return {"reports": {}}

    try:
        with open(cache_path) as f:
            cache_data = json.load(f)
        if isinstance(cache_data, dict) and "reports" in cache_data:
            return cache_data
    except (OSError, json.JSONDecodeError):
        pass

    return {"reports": {}}


def _save_report_cache(cache_data: Dict[str, Any]) -> None:
    """Persist report metadata cache to disk (best-effort)."""
    cache_path = _get_cache_path()
    try:
        with open(cache_path, "w") as f:
            json.dump(cache_data, f, indent=2)
    except OSError:
        pass


def scan_sos_reports() -> List[Dict[str, Optional[str]]]:
    """Scan SOS_REPORTS_DIR and extract metadata from each report."""
    reports = []

    cache_data = _load_report_cache()
    cached_reports = cache_data.get("reports", {})
    new_cache_reports: Dict[str, Any] = {}
    
    if not os.path.exists(SOS_REPORTS_DIR):
        return reports
    
    for item in os.listdir(SOS_REPORTS_DIR):
        item_path = os.path.join(SOS_REPORTS_DIR, item)
        
        # Only process actual directories (skip files and symlinks)
        if not os.path.isdir(item_path) or os.path.islink(item_path):
            continue

        dir_mtime = os.path.getmtime(item_path)
        cached_entry = cached_reports.get(item)

        if cached_entry and cached_entry.get("mtime") == dir_mtime:
            report_info = cached_entry.get("report", {})
        else:
            report_info = {
                "report_id": generate_report_id(item_path),
                "hostname": extract_hostname(item_path),
                "serial_number": extract_serial_number(item_path),
                "uuid": extract_uuid(item_path),
                "creation_date": extract_creation_date(item_path)
            }

        new_cache_reports[item] = {
            "mtime": dir_mtime,
            "report": report_info
        }
        reports.append(report_info)
    
    cache_data["reports"] = new_cache_reports
    _save_report_cache(cache_data)
    return reports


def query_sos_reports(hostname: Optional[str] = None, 
                     serial_number: Optional[str] = None, 
                     date_contains: Optional[str] = None) -> Dict[str, Any]:
    """Query and list available SOS reports with their metadata.
    
    Use this tool FIRST to find available SOS reports. Each report has a report_id 
    that you'll use with other tools. SOS reports contain Linux system diagnostic data.
    
    Args:
        hostname: Filter by hostname (partial match, case-insensitive)
        serial_number: Filter by hardware serial number (exact match)
        date_contains: Filter by creation date (partial match)
    
    Returns:
        Dictionary with 'reports' list containing report metadata including:
        - report_id: Simplified ID for use with other tools (e.g., "centos9-original_20251209_1430")
        - report_name: Original directory name 
        - hostname: Extracted hostname from the report
        - serial_number: Hardware serial number
        - creation_date: When the report was created
        
    Example: First call query_sos_reports() to get report_id, then use that with 
    other tools like read_file(report="centos9-original_20251209_1430", path="etc/hostname")
    """
    all_reports = scan_sos_reports()
    filtered_reports = []
    
    for report in all_reports:
        # Apply filters
        if hostname and (not report["hostname"] or hostname.lower() not in report["hostname"].lower()):
            continue
        if serial_number and report["serial_number"] != serial_number:
            continue
        if date_contains and (not report["creation_date"] or date_contains not in report["creation_date"]):
            continue
        
        filtered_reports.append(report)
    
    # Apply list limits (Layer 1: Smart truncation)
    result = limit_list(filtered_reports)
    
    response_data = {
        "reports": result["items"],
        "truncated": result["truncated"],
        "total_found": result["total_count"],
        "showing": len(result["items"])
    }
    
    # Apply hard size limit (Layer 2: Emergency brake)
    return enforce_response_size_limit(response_data)