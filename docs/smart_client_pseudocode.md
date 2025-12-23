// =======================================
// LLM → CLIENT RESPONSE SCHEMAS
// =======================================

// This pseudocode defines the entire MCP client control loop.
// The client is a simple state machine that drives an investigation.
// The LLM acts only as a planner and MUST emit exactly one JSON object
// matching one of the allowed response schemas.
//
// States:
//   START        - user question received
//   THINKING     - waiting for LLM to choose next action
//   TOOL_RUN     - MCP server tool invocation
//   WAIT_USER    - waiting for user input
//   END          - investigation complete
//
// The client strictly enforces the JSON schemas and state transitions.
// Any invalid or non-conforming LLM output is rejected and retried.
// The client contains no SOS-specific logic; all reasoning lives in the LLM.

SCHEMA call_tool = {
    type: "object",
    required: ["action", "tool", "args", "reason"],
    properties: {
        action: { const: "call_tool" },
        tool:   { type: "string" },
        args:   { type: "object" },
        reason: { type: "string" }
    },
    additionalProperties: false
}

SCHEMA ask_user = {
    type: "object",
    required: ["action", "question", "why"],
    properties: {
        action:   { const: "ask_user" },
        question: { type: "string" },
        why:      { type: "string" }
    },
    additionalProperties: false
}

SCHEMA answer_user = {
    type: "object",
    required: ["action", "answer"],
    properties: {
        action:     { const: "answer_user" },
        answer:     { type: "string" },
        confidence: { type: "number" }
    },
    additionalProperties: false
}

ALLOWED_SCHEMAS = [call_tool, ask_user, answer_user]

// =======================================
// PROGRAMMATIC CONTROL LOOP
// =======================================

state = {
    question: user_input,
    context: []
}

while true:

    llm_response = call_llm(
        question = state.question,
        context  = state.context,
        protocol = ALLOWED_SCHEMAS
    )

    if not valid_json(llm_response):
        continue  // retry hard

    if not matches_any_schema(llm_response, ALLOWED_SCHEMAS):
        continue  // retry hard

    if llm_response.action == "call_tool":

        tool_result = call_mcp_server(
            tool = llm_response.tool,
            args = llm_response.args
        )

        state.context.append({
            "tool": llm_response.tool,
            "result": tool_result
        })

        continue

    if llm_response.action == "ask_user":

        user_reply = ask_user(
            question = llm_response.question
        )

        state.context.append({
            "user_fact": user_reply
        })

        continue

    if llm_response.action == "answer_user":

        output_to_user(llm_response.answer)
        break  // END INVESTIGATION