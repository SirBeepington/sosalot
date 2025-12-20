TASK LIST: Tool self-description cleanup and standardising tool behaviours

[ ] 1. Separate tool contracts from client guidance
    - Remove workflow advice and design rationale from all tool docstrings
      - Delete phrases like “Use this tool FIRST…”
      - Remove cross-tool usage examples
      - Remove explanations of *why* behaviours exist
    - Keep tool docstrings limited to:
      - what the tool does
      - arguments
      - return fields
      - behavioural guarantees and constraints
    ..we'll add the removed guidance to the new tool-guide resource, see below.

[ ] 2. Clarify and separate resource responsibilities
    - Keep sos://report-layout focused on:
      - sosreport directory structure
      - file layout and conventions
      - meaning of common paths and files
    - Create sos://tool-guide focused on:
      - how to use the MCP server tools together
      - canonical investigation flows
      - tool selection guidance
      - rationale for differing tool behaviours (e.g. pagination)
    - Ensure there is no overlap between the two resources

[ ] 3. Define and document pagination behaviour per tool (contracts only)
    - read_file:
      - State that pagination is stream-style (offset/limit)
      - Document returned fields:
        - offset
        - next_offset
        - eof (true/false)
    - list_dir:
      - State that results are bounded (max_items + truncated)
      - Explicitly state that results are not pageable
      - Document ordering (lexical)
    - search tools:
      - Explicitly state that results are truncated and not pageable

[ ] 4. Make return schemas explicit everywhere
    - Replace vague phrases like “Dictionary with search results”
    - For every tool, list returned fields by name
    - Standardize list field naming:
      - Use `items` for all list results (not `matches`, `reports`, etc.)
      - Use `total_items` consistently (not `total_found`, `total_matches`, etc.)
    - Ensure all list-returning tools include:
      - items (the actual list data)
      - truncated (boolean), where applicable
      - total_items (count), where applicable

[ ] 5. Rename search_for_files_and_directories
    - Choose a shorter, clearer name:
      - find_paths (recommended - clear and concise)
      - glob_paths (alternative - explicitly mentions globbing)
      - search_paths (alternative - but still long)
    - Update:
      - tool name
      - docstring
      - any references in sos://tool-guide

[ ] 6. Clarify text handling assumptions (contract-level)
    - In read_file documentation, specify:
      - encoding (UTF-8)
      - behaviour on decode errors (replace / ignore)
      - line endings preserved as-is
      - binary file handling (error/skip behavior)
      - large file limits (if any)

[ ] 7. Terminology consistency pass
    - Pick one and standardise everywhere:
      - “SOS report” vs “sosreport”
      - report vs report_id
    - Apply consistently across:
      - tools
      - resources
      - examples

[ ] 8. Final LLM sanity pass
    - Read all tool contracts consecutively
    - Check:
      - no workflow advice in contracts
      - no rationale leaking into tool descriptions
      - no implied ordering between tools
    - Ask: “Could a dumb but obedient LLM use this correctly?”