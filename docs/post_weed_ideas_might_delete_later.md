# Post-Weed Ideas (Might Delete Later)

=========

# LLM's notes

## Embedded prompts in MCP code, in the docstrings

You're absolutely **not** tripping - you've identified a **separation of concerns** problem. Right now we're mixing:
- **Business Logic** (code that does work)
- **Interface Contracts** (what the LLM needs to know)
- **Prompt Engineering** (how to communicate with LLMs)

## The Problem with Current Patterns

Looking at your SOSALot server, the tool docstrings serve **dual purposes**:
```python
def list_available_reports():
    """
    List all available SOS reports with simplified IDs.
    Returns clean report metadata for LLM consumption.
    """
    # ^ This becomes part of the LLM's context
    # ^ But it's also buried in your Python code
```

## Better Architecture Pattern

Consider a **prompt configuration layer**:

```yaml
# prompts/mcp_tools.yaml
tools:
  list_available_reports:
    description: "Find available SOS reports. Returns simplified IDs like 'centos9-original_20251209_2142' instead of complex directory names."
    examples:
      - "Show me all available reports"
      - "What SOS reports can I analyze?"
    response_format: "JSON with report_id, system, and date fields"
    
  get_system_info:
    description: "Extract key system information from a specific report."
    parameters:
      report_id: "Use simplified report ID from list_available_reports"
    examples:
      - "What OS is running on centos9-original_20251209_2142?"
      - "Get system details for this report"
```

Then your code becomes pure utility:
```python
class SOSALotServer:
    def __init__(self, prompt_config_path):
        self.prompts = PromptManager(prompt_config_path)
        
    @tool
    def list_available_reports(self):
        # Pure business logic - no LLM-specific text
        return self._discover_reports()
        
    def get_tool_schema(self):
        # Tool registration uses external prompts
        return self.prompts.generate_mcp_schema()
```

========


# Greg's notes

## Diagnostic Recipes as MCP Resources (Rember to set up resources/list if you do this)

**The Idea**: MCP server contains diagnostic "recipes" for common system problems. When user says "networking is slow", LLM gets structured investigation workflow.

Eg..

```
sos://recipes                    # Index of available recipes  
sos://recipe/network-performance # Network diagnostic workflow
sos://recipe/storage-issues      # Disk/filesystem problems
sos://recipe/memory-leaks        # Memory investigation steps
```

**Example Recipe Resource:**
```yaml
name: "Network Performance Investigation"
triggers: ["slow network", "connectivity problems"] 
steps:
  - check_interface_errors:
      files: ["/proc/net/dev", "/var/log/messages"]
      look_for: ["CRC errors", "dropped packets"]
  
  - analyze_dns_config:
      files: ["/etc/resolv.conf"] 
      flags: ["mixed network ranges", "unreachable nameservers"]
```


## Problem with abstracting prompts from code.

The problem with abstracting the prompt layer is that you then have two sources of behavioural 'truth'..
> The prompt, in the prompt layer
> The actual code that makes the prompt's boasts come true, buried in the python code.
..the answer to this is probably in the realms of JIT code (unworkable for me) or maybe JIT arranging of existing logical code blocks like mini arrangable tools (still probably a bit far fetched).

## Anthropic's MCP "Code Mode"

"Code execution with MCP" https://www.anthropic.com/engineering/code-execution-with-mcp

In this the MCP server exposes tools as commands in a kiiiiind of shell like environment. 
Not sure if I really understand this, but worth looking in to.