# SOSALot - SOS Report Analysis via MCP

**SOSALot** is a Model Context Protocol (MCP) server that provides LLM-friendly APIs to retrieve data from Linux SOS reports. 

### Design

Provide a smart lookup tool to find a specified SOS report's files by specified info domain. 

Use separate config to list common sos file paths (globbing allowed) for each of a set of info domains. The lookup tool whne given a domain and specific sos report should return only files of interest to that domain that do exist on the sos report expanding globing if present.

Provide fallback file search tools.

This is as an alt4ernative to providing comprehensive tooling to abstract data from SOS reports which due to differences between report and OS versions are likely to be brittle and costly to maintain.

#### Benefits
 - **Maintainability**: Update config to maintain and extend functionality
 - **Reliability**: Generic file operations are immune to SOS report version variations

#### Drawbacks
 - **Domain knowledge**: Demands linux knowledge from client to interpret file contents, often linux command outputs.


## Quick Start

### Prerequisites
- Python 3.8+

### Server Setup on linux/macOS

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate 

# Install dependencies
pip install -r requirements.txt
```
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
      "command": "/Users/gandalf/Documents/MCP-SERVERS/sosalot/venv/bin/python",
      "args": [
        "/Users/gandalf/Documents/MCP-SERVERS/sosalot/sosalot_server.py",
        "-t",
        "stdio"
      ]
    }
  }
}
```

