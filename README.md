# SOSALot - SOS Report Analysis via MCP

**SOSALot** (SOS A Lot) is a Model Context Protocol (MCP) server that provides LLM-friendly APIs for analyzing Linux SOS reports. 

## Project Structure

This is a **monorepo** with two independent packages:

```
sosalot/
├── sosalotserver/          # MCP Server Package
│   ├── sosalot_server.py   # Main MCP server
│   ├── utils.py            # Utility functions
│   ├── tools/              # MCP tools implementation
│   ├── sos_reports/        # Sample SOS report data
│   └── requirements.txt    # Server dependencies
├── sosalotclient/          # Client Package  
│   ├── test_sosalot_client.py     # Comprehensive test suite
│   ├── mcp_client_basic_func.py   # LLM integration client
│   └── requirements.txt           # Client dependencies
└── README.md
```

## Features

### SOS Report Analysis Tools
- **Report Discovery**: Find and list available SOS reports
- **System Information**: Extract hardware, OS, and configuration data
- **File System Analysis**: Navigate and analyze captured file systems
- **Performance Data**: Access system metrics and logs


## Quick Start

### Prerequisites
- Python 3.8+

### Server Setup

```bash
# Navigate to server directory
cd sosalotserver/

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the MCP server
python sosalot_server.py
```

### Client Setup

```bash
# Navigate to client directory (in a new terminal)
cd sosalotclient/

# Create and activate virtual environment  
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests to verify setup
python test_sosalot_client.py
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
- **MCP Documentation**: https://modelcontextprotocol.io/
- **SOS Report Documentation**: https://github.com/sosreport/sos

---

**SOSALot** 