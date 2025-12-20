#!/usr/bin/env python3
"""
SosAlot Report Discovery Tools

Tools for discovering and querying available SOS reports.
"""

import os
from typing import Dict, List, Optional, Any

from utils import (
    SOS_REPORTS_DIR,
    extract_hostname,
    extract_serial_number,
    extract_uuid,
    extract_creation_date,
    generate_report_id,
    ensure_report_symlink,
    limit_list,
    enforce_response_size_limit
)


def scan_sos_reports() -> List[Dict[str, Optional[str]]]:
    """Scan SOS_REPORTS_DIR and extract metadata from each report."""
    reports = []
    
    if not os.path.exists(SOS_REPORTS_DIR):
        return reports
    
    for item in os.listdir(SOS_REPORTS_DIR):
        item_path = os.path.join(SOS_REPORTS_DIR, item)
        
        # Skip symlinks (our simplified IDs) - only process actual directories
        if os.path.isdir(item_path) and not os.path.islink(item_path):
            # Create symlink and get simplified ID
            simplified_id = ensure_report_symlink(item_path)
            
            report_info = {
                "report_id": simplified_id,  # Simplified ID for LLM use
                "hostname": extract_hostname(item_path),
                "serial_number": extract_serial_number(item_path),
                "uuid": extract_uuid(item_path),
                "creation_date": extract_creation_date(item_path)
            }
            reports.append(report_info)
    
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