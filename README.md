# SOSALot - SOS Report Analysis via MCP

**SOSALot** is a Model Context Protocol (MCP) server that provides LLM-friendly APIs to retrieve data from Linux SOS reports. 

### Design Philosophy

SOS report outputs vary between target systems, distros and sos report versions. 

Comprehensive MCP tooling to abstract data from sos reports (e.g., `get_network_interfaces`, `get_hardware_info` etc.) will be complex and brittle.

So we provide a tool "get_info_sources_for_domain" to find the right files. Plus tools to read, list, find and search within files.

We maintain JSON config for "get_info_sources_for_domain" which lists common sos file paths (globbing allowed) for each of a set of info domains. When the tool is called with a specified info domain and sos report we return only files of interest to that domain that do exist on the sos report expanding globing if present.

Additionaly we provide a tool to discover sos reports. May be useful to write a tool that provides filtering for journal data.

#### Benefits
 - **Maintainability**: Update configuration files instead of code to amend and extend functionality
 - **Reliability**: Generic file operations are immune to SOS report version variations
 - **Flexibility**: All the data in any given sos report can be made available

#### Drawbacks
 - **File names and directory structure**: Very linux-like, demands good linux knowledge from client
 - **No data abstraction**: Difficulty diffing sos reports that don't have matching files 



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
