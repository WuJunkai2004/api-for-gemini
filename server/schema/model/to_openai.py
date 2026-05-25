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

    for content in req.contents:
        role = "assistant" if content.role == "model" else "user"

        if not content.parts:
            continue

        text_content = "".join([p.text for p in content.parts if p.text])

        if text_content:
            messages.append({"role": role, "content": text_content})

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
