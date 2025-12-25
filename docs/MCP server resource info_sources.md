# MCP Resource Specification  
## `info_sources/<domain_name>`

---

## Background

This resource represents a **configuration-driven architecture** choice for SOS report analysis.

### Design Philosophy

Rather than building dozens of specialized tools (`get_network_interfaces()`, `get_hardware_info()`, etc.), this approach leverages:

- **Generic file tools**: `read_file()`, `search_file()`, `list_dir()` - bulletproof and version-agnostic
- **Smart signposting**: Resources guide clients to the right data sources  
- **Configuration intelligence**: Domain knowledge lives in declarative config, not code
- **AI interpretation**: LLMs handle content analysis using simple, reliable file operations

### Strategic Benefits

**Maintainability**: When SOS report formats change or new domains emerge, update configuration files instead of rebuilding tools.

**Extensibility**: New information domains require no code changes - just config updates.

**Reliability**: Generic file operations are immune to SOS report version variations.

**Efficiency**: Clients get targeted guidance without sacrificing the flexibility of generic tools.

### Core Insight

**Intelligence belongs in configuration, not code.** The MCP server provides smart signposting; the client (LLM) handles interpretation using proven file manipulation primitives.

---

## Purpose

This resource exposes **report-specific, domain-scoped information sources** to MCP clients, based on a **static, declarative server configuration**.

It answers one question only:

> *For this SOS report, which sources should be consulted for this category of information?*

At present, these sources are filesystem objects (files, symlinks, directories), but the abstraction is intentionally broader.

This resource **does not**:
- parse file contents
- summarise data
- infer meaning
- guarantee completeness
- assert correctness of the information contained

---

## Resource Characteristics

- **Type**: Resource (not a tool)
- **Mutability**: Dynamic per report
- **Side effects**: None
- **Idempotent**: Yes
- **Cost**: Low (filesystem existence checks + glob expansion)

---

## Resource Naming

Pattern:

```
info_sources/<domain_name>
```

Examples:
- `info_sources/network_interfaces`
- `info_sources/routing`
- `info_sources/kernel`
- `info_sources/hardware`

`<domain_name>` **must correspond** to a domain defined in the MCP server configuration.

The name intentionally emphasises *sources*, not answers or facts.

---

## Resource Inputs

| Field  | Type   | Required | Description |
|------|--------|----------|-------------|
| `report` | string | Yes | SOS report identifier |

No other inputs are accepted.

---

## Resource Output Schema

```json
{
  "domain": "network_interfaces",
  "description": "Network interface addresses and link-level information",
  "report": "centos9-original_20251209_2142",
  "sources": [
    {
      "path": "sos_commands/networking/ip_-o_addr",
      "source_type": "file",
      "confidence": "high",
      "notes": "Primary source of IPv4 and IPv6 interface addresses"
    },
    {
      "path": "sos_commands/networking/ip_addr",
      "source_type": "symlink",
      "confidence": "medium",
      "notes": "Alternate ip addr output, may point to preferred source"
    }
  ],
  "missing_sources": [
    {
      "pattern": "sos_commands/networking/ifconfig*",
      "confidence": "low",
      "notes": "Legacy net-tools output, often absent on modern systems"
    }
  ]
}
```

---

## Output Semantics

### `sources`
- Contains **only sources that exist** in the specified report
- Ordered by preference (as defined in configuration)
- Sources may be files, directories, or symlinks
- No guarantee of completeness or uniqueness

### `missing_sources`
- Lists configured paths or globs that did **not** match
- Included to make absence explicit and meaningful
- Absence is informational, not an error

If no sources exist, `sources` is an empty array.  
This is **not an error condition**.

---

## Error Conditions

| Condition | Behaviour |
|---------|-----------|
| Unknown domain | Resource not found |
| Unknown report | Resource error |
| Filesystem error | Resource error |

Partial results are not returned.

---

# MCP Server Configuration  
## Info Sources Configuration

---

## Purpose

This configuration defines:
- information domains
- ranked information sources per domain
- human- and LLM-readable intent and caveats

It is:
- static
- version-controlled
- authoritative

The MCP server:
- loads it at startup
- does not mutate it
- does not interpret beyond glob expansion and existence checks

---

## Configuration Structure

```json
{
  "info_sources": {
    "<domain_name>": {
      "description": "...",
      "sources": [
        { /* source definition */ }
      ]
    }
  }
}
```

---

## Domain Definition

Each top-level entry represents an **information domain**.

### Fields

| Field | Type | Required | Description |
|------|------|----------|-------------|
| `description` | string | Yes | Short, declarative description of the domain |
| `sources` | array | Yes | Ordered list of candidate information sources |

---

## Source Definition

Each source entry must contain **exactly one** of `path` or `glob`.

### Path Source

```json
{
  "path": "sos_commands/networking/ip_-o_addr",
  "confidence": "high",
  "notes": "Primary source of interface addresses"
}
```

### Glob Source

```json
{
  "glob": "sos_commands/networking/ifconfig*",
  "confidence": "low",
  "notes": "Legacy net-tools output, may be absent"
}
```

---

## Source Rules

- Exactly one of `path` or `glob` is required
- Recursive globs (`**`) are not permitted
- Globs are expanded **within the report root only**
- Source order defines preference
- Confidence is informational only and does not affect behaviour

---

## Allowed Confidence Values

```
high
medium
low
```

No numeric scoring or weighting logic is applied.

---

## Example Configuration

```json
{
  "info_sources": {
    "network_interfaces": {
      "description": "Network interface addresses and link-level state",
      "sources": [
        {
          "path": "sos_commands/networking/ip_-o_addr",
          "confidence": "high",
          "notes": "Primary source of IPv4 and IPv6 addresses"
        },
        {
          "path": "sos_commands/networking/ip_addr",
          "confidence": "medium",
          "notes": "Alternate ip addr output or symlink"
        },
        {
          "glob": "sos_commands/networking/ifconfig*",
          "confidence": "low",
          "notes": "Legacy net-tools output"
        }
      ]
    }
  }
}
```

---

## Explicit Non-Goals

This configuration must **not** include:
- parsing instructions
- regular expressions
- distro or version conditionals
- semantic extraction hints
- execution logic

If such behaviour is required, it belongs in a **tool**, not a resource.

---

## Contract Summary

- Configuration defines **intent and preference**
- `info_sources/<domain>` reports **actual sources present for a specific report**
- Interpretation and synthesis are performed by the MCP client (LLM)
- The MCP server remains simple, deterministic, and stable