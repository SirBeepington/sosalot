#!/usr/bin/env python3
"""
Info Sources Tool

Provides domain-specific information source guidance for SOS reports.
"""

import os
import json
import glob
from typing import Dict, List, Any, Optional
from utils import SOS_REPORTS_DIR, resolve_report_dir


def load_info_sources_config() -> Dict[str, Any]:
    """Load info sources configuration from JSON file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "..", "config", "info_sources.json")
    
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise RuntimeError(f"Info sources configuration not found: {config_path}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in info sources config: {e}")


def check_source_exists(report: str, source_def: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Check if a configured source exists in the specified report.
    
    Args:
        report: Report ID (e.g., "centos9-original_20251209_2142")
        source_def: Source definition from config
        
    Returns:
        Source info dict if exists, None if not found
    """
    report_dir = resolve_report_dir(report)
    report_path = os.path.join(SOS_REPORTS_DIR, report_dir) if report_dir else os.path.join(SOS_REPORTS_DIR, report)
    
    if not os.path.exists(report_path):
        raise ValueError(f"Report not found: {report}")
    
    # Handle path-based sources
    if "path" in source_def:
        source_path = os.path.join(report_path, source_def["path"])
        if os.path.exists(source_path):
            return {
                "path": source_def["path"],
                "confidence": source_def.get("confidence", "medium"),
                "notes": source_def.get("notes", "")
            }
    
    # Handle glob-based sources
    elif "glob" in source_def:
        glob_pattern = os.path.join(report_path, source_def["glob"])
        matches = glob.glob(glob_pattern)
        
        if matches:
            # Convert absolute paths to relative paths within the report
            relative_matches = [os.path.relpath(match, report_path) for match in matches]
            
            return {
                "glob": source_def["glob"],
                "found_paths": relative_matches,
                "confidence": source_def.get("confidence", "medium"),
                "notes": source_def.get("notes", "")
            }
    
    # Source not found
    return None


def get_info_sources(domain: str, report: str) -> Dict[str, Any]:
    """Get information sources for a domain in a specific report.
    
    Args:
        domain: Information domain name (e.g., "network_interfaces")
        report: Report ID (e.g., "centos9-original_20251209_2142")
        
    Returns:
        Resource response with sources that actually exist in the report
        
    Raises:
        ValueError: If domain or report not found
    """
    config = load_info_sources_config()
    
    if domain not in config.get("info_sources", {}):
        raise ValueError(f"Unknown domain: {domain}")
    
    domain_config = config["info_sources"][domain]
    
    # Build list of sources that actually exist in this report
    existing_sources = []
    
    # Check each configured source and only keep those that exist
    for source_def in domain_config.get("sources", []):
        source_info = check_source_exists(report, source_def)
        
        if source_info:
            existing_sources.append(source_info)
    
    return {
        "domain": domain,
        "description": domain_config.get("description", ""),
        "report": report,
        "sources": existing_sources
    }


def list_available_domains() -> List[str]:
    """Get list of all configured information domains."""
    config = load_info_sources_config()
    return list(config.get("info_sources", {}).keys())


def get_info_sources_for_domain(domain: str, report: str) -> str:
    """Get information source guidance for a specific domain in a SOS report.
    
    This tool provides intelligent guidance on where to find specific types of
    information within SOS reports, returning only files that actually exist
    in the specified report.
    
    Args:
        domain: Information domain to get guidance for. Must be one of:
                [DOMAINS_PLACEHOLDER]
        report: SOS report ID to search within (e.g., "centos9-original_20251209_2142").
                Use query_sos_reports() tool first to get available report IDs.
    
    Returns:
        JSON string with structured guidance showing actual existing files
        for the specified domain in the given report. Only returns files that
        exist - no placeholders or missing file indicators.
    """
    try:
        result = get_info_sources(domain, report)
        return json.dumps(result, indent=2)
    except ValueError as e:
        # Return available domains if invalid domain provided
        available = list_available_domains()
        return json.dumps({
            "error": str(e),
            "available_domains": available
        }, indent=2)


# Dynamically update the docstring with current domains from config
try:
    config = load_info_sources_config()
    domain_info = []
    for domain, details in config.get("info_sources", {}).items():
        description = details.get("description", "")
        domain_info.append(f"        {domain}: {description}")
    
    domain_list = "\n".join(domain_info)
    get_info_sources_for_domain.__doc__ = get_info_sources_for_domain.__doc__.replace(
        "[DOMAINS_PLACEHOLDER]", f"\n{domain_list}"
    )
except Exception:
    # Fallback if config loading fails
    get_info_sources_for_domain.__doc__ = get_info_sources_for_domain.__doc__.replace(
        "[DOMAINS_PLACEHOLDER]", "check error responses for available domains"
    )