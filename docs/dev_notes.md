#### Development Notes

## Coding Style - Functional Preference
- **Use functional approach** where possible (user preference)
- **Minimal OO only when required** by MCP SDK
- Pattern: `sosalot = FastMCP("SosAlot")` + functional tools
**Functional:** Tool functions, utilities, client code  
**OO Required:** FastMCP server, ClientSession (SDK handles complexity)

## MCP Server Paradigms and Best Practices
- Session-based: The client opens a persistent streamable-http connection and exchanges multiple MCP messages over it until disconnect.
- Multi-tenant: Any number of clients can maintain their own concurrent sessions with the same server.
- Stateless: Server-side functions should not rely on stored session state; each request should carry all the context it needs.
- In as far as is feasable, we should try write the mcp server, it's tools and prompts, to provide the calling client LLM framework with all the knowledge it needs to use the tool. The calling LLM should not need any special promting to understand the kind of data and tools the serv er provides.

## Useful docs and links..
# MCP SDK quickstart webpage. We're not following this slavishly but it is useful for examples and bits of stuff:
https://pypi.org/project/mcp/

## Done/created so far

## Next actions


# Niggles..
    We need to get more sos reports from differend flavors, and multiple ones from the saem servers also. So we can check how query_sos_reports bahaves in these circumstances.

    Old and new sos_reports format issues:
    - If ./sos_reports/manifest.json exists → this is a new-format sosreport :D
    - If not → this is an old-format sosreport [sadface]
    ..this might be a problem if we start o rely on date in manifest.json, at the moment we are not so we can remain agnostic about this version difference.. if we do find we need manifest.json we should think about ignoring sos reports that have no manigest.json (as I think modern our estate uses the new one anyway).
    OR .. can we check reliable to get the sos report version and then discard any that are not wihtin a range of compatible versions? Is this reliable between linux flavors (ie, do all flavors, centos, rhel, rocky use the same versioning on their respective sos report tools?).. REMEMB ER, this is for work to run on rhel/centos/rocky installs of 8 and above, we can always expect sosreport to be upgraded to laterst before we generate it.


# DSPy for the client?
DSPy is a framework for COT Agentic flow (I think) and it's party trick is to autotune prompts (it also can tune weghts but that's beyond my meagre hardware).
Maybe when we right the client end we could use that?