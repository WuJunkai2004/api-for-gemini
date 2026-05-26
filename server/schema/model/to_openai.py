import json
from google.genai.types import Schema as GeminiSchema, Type

from server.schema.request import GoogleRequest


_TYPE_MAP = {
    Type.STRING: "string",
    Type.NUMBER: "number",
    Type.INTEGER: "integer",
    Type.BOOLEAN: "boolean",
    Type.ARRAY: "array",
    Type.OBJECT: "object",
}


def _convert_schema(schema: GeminiSchema) -> dict:
    json_schema: dict = {}
    if schema.type is not None:
        json_schema["type"] = _TYPE_MAP.get(schema.type, "string")
    if schema.description is not None:
        json_schema["description"] = schema.description
    if schema.enum:
        json_schema["enum"] = schema.enum
    if schema.format is not None:
        json_schema["format"] = schema.format
    if schema.default is not None:
        json_schema["default"] = schema.default
    if schema.nullable:
        json_schema["nullable"] = True
    if schema.properties:
        json_schema["properties"] = {
            k: _convert_schema(v) for k, v in schema.properties.items()
        }
    if schema.required:
        json_schema["required"] = schema.required
    if schema.items:
        json_schema["items"] = _convert_schema(schema.items)
    return json_schema


def _convert_tools(tools) -> list[dict] | None:
    openai_tools = []
    for tool in tools:
        if not tool.function_declarations:
            continue
        for fd in tool.function_declarations:
            ot: dict = {
                "type": "function",
                "function": {
                    "name": fd.name,
                    "description": fd.description or "",
                },
            }
            if fd.parameters:
                ot["function"]["parameters"] = _convert_schema(fd.parameters)
            openai_tools.append(ot)
    return openai_tools or None


def transfer(req: GoogleRequest, target_model: str, isStream: bool):
    messages = []

    if req.system_instruction and req.system_instruction.parts:
        sys_text = "".join([p.text for p in req.system_instruction.parts if p.text])
        if sys_text:
            messages.append({"role": "system", "content": sys_text})

    # Track call IDs to match responses
    # Gemini doesn't always provide IDs, so we might need to match by name in simple cases
    # or track them sequentially.
    call_id_map = {} # name -> id

    for content in req.contents:
        role = "assistant" if content.role == "model" else "user"
        
        text_content = ""
        reasoning_content = ""
        tool_calls = []
        
        for part in content.parts:
            # Handle thought parts for thinking models
            if getattr(part, "thought", False):
                reasoning_content += part.text or ""
                continue

            if part.text:
                text_content += part.text
            
            if part.function_call:
                # Map Gemini function_call to OpenAI tool_call
                call_id = getattr(part.function_call, "id", None) or f"call_{len(messages)}_{len(tool_calls)}"
                call_id_map[part.function_call.name] = call_id
                tool_calls.append({
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": part.function_call.name,
                        "arguments": json.dumps(part.function_call.args) if part.function_call.args else "{}"
                    }
                })
            
            if part.function_response:
                # Gemini function_response -> OpenAI tool role message
                name = part.function_response.name
                call_id = getattr(part.function_response, "id", None) or call_id_map.get(name, f"call_{name}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps(part.function_response.response) if part.function_response.response else ""
                })

        if text_content or reasoning_content or tool_calls:
            msg = {"role": role, "content": text_content if text_content else None}
            if reasoning_content:
                msg["reasoning_content"] = reasoning_content
            if tool_calls:
                msg["tool_calls"] = tool_calls
            messages.append(msg)

    # Handle "Thinking" models (like DeepSeek R1) which don't support Assistant Prefill
    is_thinking_model = any(kw in target_model.lower() for kw in ["reasoner", "r1"])
    
    if is_thinking_model and messages and messages[-1]["role"] == "assistant":
        # If the last message is assistant, it's a prefill or an incomplete tool turn
        last_msg = messages.pop()
        
        # If it has tool_calls, we can't really "fix" it without tool results,
        # but we can try to keep the history if there's text.
        # If it's just text prefill, we merge it into the last user message.
        if last_msg.get("content") and not last_msg.get("tool_calls"):
            if messages and messages[-1]["role"] == "user":
                messages[-1]["content"] += f"\n\n(Note: Continue the response starting with: \"{last_msg['content']}\")"
            else:
                # Fallback: convert to user message
                messages.append({"role": "user", "content": f"Please continue the response starting with: \"{last_msg['content']}\""})
        elif last_msg.get("tool_calls"):
            # If it has tool_calls, we put it back but this might still fail if it's the LAST message.
            # However, removing it would break the tool chain.
            # Most likely the client should have provided the tool results.
            messages.append(last_msg)
        # If it was empty, we just leave it popped.

    openai_kwargs = {
        "model": target_model,
        "messages": messages,
    }

    if req.generation_config:
        config = req.generation_config

        if config.temperature is not None:
            openai_kwargs["temperature"] = config.temperature

        if config.top_p is not None:
            openai_kwargs["top_p"] = config.top_p

        if config.max_output_tokens is not None:
            openai_kwargs["max_tokens"] = config.max_output_tokens

        if config.response_mime_type == "application/json":
            openai_kwargs["response_format"] = {"type": "json_object"}

    if req.tools:
        openai_tools = _convert_tools(req.tools)
        if openai_tools:
            openai_kwargs["tools"] = openai_tools

    return openai_kwargs
