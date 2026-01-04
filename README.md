# SOSALot - SOS Report Analysis via MCP

**SOSALot** is a Model Context Protocol (MCP) server that provides LLM-friendly APIs to retrieve data from Linux SOS reports. 

### Design

Provide a smart lookup tool to find a specified SOS report's files by specified info domain. 

Use separate config to list common sos file paths (globbing allowed) for each of a set of info domains. The lookup tool when given a domain and specific sos report should return only files of interest to that domain that do exist on the sos report expanding globbing if present.

Provide fallback file search tools.

This is as an alternative to providing comprehensive tooling to abstract data from SOS reports which due to differences between report and OS versions are likely to be brittle and costly to maintain.

Also, keep tool definitions in a separate config file, instead of docstrings for easier versioning and ab testing.

## Quick Start


### Prerequisites
- Python 3.8+

### Server Setup on Linux/macOS

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate 

# Install dependencies
pip install -r requirements.txt
```

### Put your extracted sos reports in ./sos_reports

Extracted reports go in ./sos_reports
MCP server needs write perms and ability to create symlinks in there.

### MCP server modes

```bash
# Option 1: STDIO mode (for direct MCP client integration).
python sosalot_server.py -t stdio

# Option 2: Streamable HTTP mode (default)  
python sosalot_server.py -t strm

# Option 3: Default mode (streamable HTTP)
python sosalot_server.py
```
### Set up under Claude Desktop

Run the server in STDIO mode

See https://modelcontextprotocol.io/docs/develop/connect-local-servers

Example claude_desktop_config.json

```JSON
{
  "preferences": {
    "quickEntryShortcut": "off",
    "menuBarEnabled": true
  },
  "mcpServers": {
    "sosalot": {
      "command": "/path/to/sosalot/.venv/bin/python",
      "args": [
        "/path/to/sosalot/sosalot_server.py",
        "-t",
        "stdio"
      ]
    }
  }
}
```
### Usage

Ask the MCP client to list sos reports, or find an sos report for a given hostname and / or date range.

Then query about the sos report itself. 
