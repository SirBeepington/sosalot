# Desired Client LLM Behaviour Examples

This document outlines the **expected user journey** and LLM behavior patterns when interacting with the SOSALot MCP server. These scenarios help us evaluate whether our tool descriptions and workflows are LLM-friendly.

## Core Principles
- **LLM should start with report discovery** when given a hostname
- **LLM should explore filesystem systematically** when looking for specific data
- **LLM should understand SOS report structure** and common file locations
- **LLM should provide specific, data-driven answers** based on actual file contents

---

## Scenario 1: Network Interface Discovery

### User Query
> "Tell me what network interfaces host centos9-original has"

### Expected LLM Workflow
1. **Query Reports**: `query_sos_reports(hostname="centos9-original")`
   - Should find `centos9-original_20251209_2142` report
   
2. **Explore Structure**: `list_dir(report="centos9-original_20251209_2142", path="")`
   - Discover top-level directories including `sos_commands/`
   
3. **Navigate to Networking**: `list_dir(report="centos9-original_20251209_2142", path="sos_commands/networking")`
   - Find networking-related command outputs
   
4. **Read Interface Data**: `read_file(report="centos9-original_20251209_2142", path="sos_commands/networking/ip_-d_address")`
   - Get actual interface configuration (equivalent to `ifconfig` output)
   
5. **Provide Answer**: Parse the data and tell user about interfaces found

### Success Criteria
- ✅ Finds the correct report using hostname
- ✅ Explores filesystem methodically 
- ✅ Locates networking data files
- ✅ Provides specific interface names and details

---

## Scenario 2: System Information Query

### User Query
> "What operating system is running on centos9-original_20251209_2142?"

### Expected LLM Workflow
1. **Direct File Access**: `read_file(report="centos9-original_20251209_2142", path="etc/os-release")`
   - Since report ID is provided, skip discovery step
   - Go straight to OS information file
   
2. **Provide Answer**: Extract OS name and version from file contents

### Success Criteria
- ✅ Recognizes that report ID is already provided
- ✅ Knows where OS information is stored (`etc/os-release`)
- ✅ Provides specific OS name and version

---

## Scenario 3: Error Investigation

### User Query
> "Are there any errors in the system logs of centos9-original_20251209_2142?"

### Expected LLM Workflow
1. **Explore Log Directory**: `list_dir(report="centos9-original_20251209_2142", path="var/log")`
   - Find available log files
   
2. **Search System Logs**: `search_file(report="centos9-original_20251209_2142", path="var/log/messages", substring="error", lines_before=1, lines_after=1)`
   - Look for error patterns in main system log
   
3. **Check Additional Logs**: May also search other logs like `secure`, `dmesg`, etc.
   
4. **Provide Summary**: List specific errors found with timestamps and context

### Success Criteria
- ✅ Explores log directory structure
- ✅ Uses search_file for efficient error hunting
- ✅ Provides specific error examples with context
- ✅ Checks multiple relevant log files

---

## Scenario 4: Hardware Information

### User Query  
> "What hardware is centos9-original running on?"

### Expected LLM Workflow
1. **Find Hardware Data**: `read_file(report="centos9-original_20251209_2142", path="sos_commands/hardware/dmidecode")`
   - Read comprehensive hardware information
   
2. **Extract Key Details**: Parse dmidecode output for:
   - System manufacturer and model
   - CPU information
   - Memory configuration
   - Serial numbers
   
3. **Provide Summary**: Present hardware details in user-friendly format

### Success Criteria
- ✅ Knows where hardware information is stored
- ✅ Can parse dmidecode output effectively
- ✅ Provides useful hardware summary

---

## Anti-Patterns to Avoid

### ❌ Wrong Report Discovery
```
LLM tries: query_sos_reports(date_contains="20251209")
Should be: query_sos_reports(hostname="centos9-original")
```

### ❌ Skipping Exploration
```
LLM tries: search_file(path="some/specific/file") immediately
Should be: list_dir() first to understand structure
```

### ❌ Ignoring Tool Results
```
LLM gets: "0 reports found"
LLM then: Continues with non-existent report ID
Should be: Recognize the issue and try different approach
```

### ❌ Generic Responses
```
LLM says: "The system has network interfaces"
Should be: "The system has eth0 (192.168.1.100) and lo (127.0.0.1)"
```

---

## Tool Usage Patterns

### Good Discovery Pattern
```
1. query_sos_reports(hostname="...") 
2. list_dir(report="...", path="")
3. list_dir(report="...", path="specific_area")
4. read_file() or search_file()
```

### Good Error Handling
```
If tool returns error:
- Try alternative approaches
- Explore filesystem to understand structure
- Don't make assumptions about file locations
```

### Good Data Extraction
```
- Read complete files when needed
- Use search_file for finding specific patterns
- Provide specific examples from actual data
- Quote relevant lines from files
```

---

## Evaluation Criteria

When testing LLM behavior, look for:

1. **Correct Tool Sequence**: Does it follow logical discovery → exploration → extraction?
2. **Parameter Usage**: Does it use appropriate filters and paths?
3. **Error Recovery**: Does it adapt when tools return errors?
4. **Data Specificity**: Does it provide actual data from files, not generic responses?
5. **Filesystem Understanding**: Does it navigate SOS report structure intelligently?

These patterns help us determine if our tool descriptions provide sufficient guidance for effective LLM operation.
