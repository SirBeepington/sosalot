# SOSALot - SOS Report Analysis via MCP

**SOSALot** is a Model Context Protocol (MCP) server that provides LLM-friendly APIs to retrieve data from Linux SOS reports. 

### Design Philosophy

SOS report outputs vary between target systems, distros and sos report versions. 

Comprehensive MCP tooling to abstract data from sos reports (e.g., `get_network_interfaces`, `get_hardware_info` etc.) will be complex and brittle.

So we provide a tool "get_info_sources_for_domain" to help find the right files. Plus tools to read, list, find and search within files.

We maintain JSON config for "get_info_sources_for_domain" which lists common sos file paths (globbing allowed) for each of a set of info domains. When the tool is called with a specified info domain and sos report we return only files of interest to that domain that do exist on the sos report expanding globing if present.

Additionaly we provide a tool to discover sos reports. May be useful to write a tool that provides filetering for journal data.

#### Benefits
 - **Maintainability**: Update configuration files instead of code to amend and extend functionality
 - **Reliability**: Generic file operations are immune to SOS report version variations
 - **Flexibility**: All the data in any given sos report can be made available

#### Drawbacks
 - **File names and directory structure**: Very linux-like, demands good linux knowledge from client
 - **No data abstraction**: Difficulty diffing sos reports that don't have matching files 


## Project Structure

This is a **monorepo** with two independent packages:

```
sosalot/
├── sosalotserver/                   # MCP Server Package
│   ├── sosalot_server.py            # Main MCP server
│   ├── utils.py                     # Utility functions
│   ├── __init__.py                  # Package initialization
│   ├── requirements.txt             # Server dependencies
│   ├── config/
│   │   └── info_sources.json        # Info domain to file mappings
│   ├── tools/                       # MCP tools implementation
│   │   ├── __init__.py
│   │   ├── filesystem_tools.py      # File operations with pagination
│   │   ├── info_sources_tool.py     # Dynamic info domain mapping
│   │   └── report_discovery.py      # SOS report discovery
│   ├── prompts/                     # LLM prompt templates
│   ├── resources/                   # Resource definitions
│   └── sos_reports/                 # Sample SOS report data
│       └── sosreport-CentOS9-Original-11223344-2025-12-09-lxetseg/
├── sosalotclient/                   # Client Package  
│   ├── sosalot_server_functional_tests.py  # Comprehensive test suite
│   ├── smart_client.py              # LLM integration client
│   ├── simple_llm_test.py           # Basic LLM test
│   └── requirements.txt             # Client dependencies
├── docs/                            # Documentation
│   ├── dev_notes.md
│   ├── to_do.md
│   └── ...
├── keys/                            # API keys (gitignored)
├── Example_ code_for_reference/     # Reference implementations
└── README.md
```



## Quick Start

### Prerequisites
- Python 3.8+

### Server Setup on linux/macOS

```bash
# Navigate to server directory
cd sosalotserver/

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate 

# Install dependencies
pip install -r requirements.txt

# Run the MCP server in different modes:

# Option 1: STDIO mode (for direct MCP client integration, useful for running it under claude desktop).)
python sosalot_server.py -t stdio

# Option 2: Streamable HTTP mode (default)  
python sosalot_server.py -t strm

# Option 3: Default mode (streamable HTTP)
python sosalot_server.py
```


## 🔧 API Reference

### Available MCP Tools

#### `list_available_reports`
Returns all available SOS reports with simplified IDs:
```json
{
  "reports": [
    {
      "report_id": "centos9-original_20251209_2142",
      "original_path": "sosreport-CentOS9-Original-11223344-2025-12-09-lxetseg",
      "system": "CentOS9-Original",
      "date": "2025-12-09"
    }
  ]
}
```

#### `get_system_info`
Extract key system information from a report:
```json
{
  "hostname": "centos9-server",
  "os_release": "CentOS Linux 9",
  "kernel": "5.14.0-642.el9.aarch64",
  "architecture": "aarch64",
  "uptime": "15 days, 3 hours"
}
```

#### `list_directory_contents`
Navigate the captured file system:
```bash
# List contents of /etc
list_directory_contents centos9-original_20251209_2142 /etc

# List log files
list_directory_contents centos9-original_20251209_2142 /var/log
```

#### `read_file_content`
Read specific files from the SOS report:
```bash
# Read system release info
read_file_content centos9-original_20251209_2142 /etc/os-release

# Check system logs
read_file_content centos9-original_20251209_2142 /var/log/messages
```

## 🧪 Testing

The client package includes a comprehensive test suite:

```bash
cd sosalotclient/
python test_sosalot_client.py
```

**Test Coverage:**
- ✅ Server connectivity and health checks
- ✅ Report discovery and listing
- ✅ System information extraction  
- ✅ File system navigation
- ✅ Error handling and edge cases
- ✅ LLM integration workflows

## 🔌 LLM Integration

Use with Claude, GPT, or any LLM that supports MCP:

```python
from mcp_client_basic_func import MCPClient

# Connect to SOSALot server
client = MCPClient("http://localhost:3000")

# Let the LLM discover and analyze reports
reports = client.call_tool("list_available_reports")
system_info = client.call_tool("get_system_info", {"report_id": "centos9-original_20251209_2142"})
```

## 🛠️ Development

### Adding New Tools
1. Create tool implementation in `sosalotserver/tools/`
2. Register in `sosalot_server.py`
3. Add tests in `sosalotclient/test_sosalot_client.py`


## Requirements

### Server Dependencies
- `mcp[cli]` - Model Context Protocol framework

### Client Dependencies  
- `mcp[cli]` - MCP client functionality
- `openai` - LLM integration support

## Links

- **GitHub Repository**: https://github.com/SirBeepington/sosalot
- **MCP Documentation**: g
- **SOS Report Documentation**: https://github.com/sosreport/sos

---

**SOSALot** 