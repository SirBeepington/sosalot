#### Development Notes

## MCP Server Paradigms and Best Practices
- Session-based: The client opens a persistent streamable-http connection and exchanges multiple MCP messages over it until disconnect.
- Multi-tenant: Any number of clients can maintain their own concurrent sessions with the same server.
- Stateless: **Server-side functions should not rely on stored session state**; each request should carry all the context it needs.
- In as far as is feasable, we should try write the mcp server, it's tools and prompts, to provide the calling client LLM framework with all the knowledge it needs to use the tool. The calling LLM should not need any special promting to understand the kind of data and tools the serv er provides.
