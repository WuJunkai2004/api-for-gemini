import json
from typing import Any, Optional, Union

from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageFunctionToolCallParam,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCallUnionParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolChoiceOptionParam,
    ChatCompletionToolMessageParam,
    ChatCompletionToolParam,
    ChatCompletionUserMessageParam,
)

from api_for_gemini.server.schema.model.base import ClientRequest
from api_for_gemini.server.schema.request import APIRequest


def clean_json_schema(schema: dict):
    if not isinstance(schema, dict):
        return schema

    result = schema.copy()

    # 1. 强制把 type 转换成小写
    if "type" in result and isinstance(result["type"], str):
        result["type"] = result["type"].lower()

    # 2. 处理 object 类型
    if result.get("type") == "object":
        # 递归处理嵌套的 properties
        if "properties" in result:
            for key, val in result["properties"].items():
                result["properties"][key] = clean_json_schema(val)

    # 3. 处理 array 类型
    if result.get("type") == "array" and "items" in result:
        result["items"] = clean_json_schema(result["items"])

    return result


class OpenaiRequest(ClientRequest):
    model: str
    messages: list[ChatCompletionMessageParam]
    stream: Optional[bool] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    stop: Optional[Union[str, list[str]]] = None
    tools: Optional[list[ChatCompletionToolParam]] = None
    tool_choice: Optional[ChatCompletionToolChoiceOptionParam] = None
    response_format: Optional[dict[str, Any]] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    n: Optional[int] = None
    user: Optional[str] = None
    # For reasoning models
    reasoning_effort: Optional[str] = None
    # For DeepSeek / reasoning models
    extra_body: Optional[dict[str, Any]] = None
    stream_options: Optional[dict[str, Any]] = None

    @staticmethod
    def build(
        data: APIRequest, model_name: str, isStream: bool = False
    ) -> "OpenaiRequest":
        messages: list[ChatCompletionMessageParam] = []
        # Add system instruction as the first message if it exists
        if data.system_instruction and data.system_instruction.parts:
            messages.append(
                ChatCompletionSystemMessageParam(
                    role="system",
                    content="".join(
                        part.text for part in data.system_instruction.parts if part.text
                    ),
                )
            )

        # Add user messages
        for content in data.contents:
            if not content.parts:
                continue
            texts: list[str] = []
            thoughts: list[str] = []
            tools: list[ChatCompletionMessageToolCallUnionParam] = []
            role = {
                "model": "assistant",
                "user": "user",
            }.get(content.role or "", None)
            if not role:
                raise ValueError(f"Unsupported role: {content.role}")
            for part in content.parts:
                # 处理工具调用
                if part.function_call:
                    tools.append(
                        ChatCompletionMessageFunctionToolCallParam(
                            type="function",
                            id=getattr(
                                part.function_call,
                                "id",
                                f"call_{part.function_call.name}",
                            ),
                            function={
                                "name": part.function_call.name or "function",
                                "arguments": json.dumps(
                                    part.function_call.args, ensure_ascii=False
                                ),
                            },
                        )
                    )
                    continue

                # 处理工具调用的结果
                if part.function_response:
                    messages.append(
                        ChatCompletionToolMessageParam(
                            role="tool",
                            tool_call_id=getattr(
                                part.function_response,
                                "id",
                                f"call_{part.function_response.name}",
                            ),
                            content=json.dumps(part.function_response.response or {}),
                        )
                    )
                    continue

                # 处理文本和思考
                if part.thought:
                    thoughts.append(part.text or "")
                else:
                    texts.append(part.text or "")

            if role == "user":
                if len(texts) == 0:
                    continue
                messages.append(
                    ChatCompletionUserMessageParam(role="user", content="".join(texts))
                )
            elif role == "assistant":
                payload = {
                    "role": "assistant",
                    "content": "".join(texts),
                }
                if tools:
                    payload["tool_calls"] = tools  # type: ignore
                messages.append(
                    ChatCompletionAssistantMessageParam(
                        **payload,  # type: ignore
                    )
                )
            if role == "user" and len(tools) > 0:
                raise RuntimeError("User message cannot contain tool calls")

        # Handle tools
        openai_tools: list[ChatCompletionToolParam] = []
        for tool in data.tools or []:
            if not tool.function_declarations:
                continue
            for func_decl in tool.function_declarations:
                params = func_decl.parameters_json_schema
                if not params:
                    params = {"type": "object", "properties": {}}
                openai_tools.append(
                    ChatCompletionToolParam(
                        type="function",
                        function={
                            "name": func_decl.name or "function",
                            "description": func_decl.description or "Unknown function",
                            "parameters": params,
                        },
                    )
                )

        # Handle generation config
        temperature = None
        top_p = None
        max_tokens = None
        stop = None
        presence_penalty = None
        frequency_penalty = None
        tool_choice = None
        response_format = None
        reasoning_effort = None

        if data.generation_config:
            gc = data.generation_config
            temperature = gc.temperature
            top_p = gc.top_p
            max_tokens = gc.max_output_tokens
            stop = gc.stop_sequences
            presence_penalty = gc.presence_penalty
            frequency_penalty = gc.frequency_penalty

            if gc.response_mime_type == "application/json":
                if gc.response_json_schema:
                    response_format = {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "response",
                            "schema": clean_json_schema(gc.response_json_schema),
                        },
                    }
                else:
                    response_format = {"type": "json_object"}

            if gc.tool_config and gc.tool_config.function_calling_config:
                fcc = gc.tool_config.function_calling_config
                if fcc.mode == "ANY":
                    tool_choice = "required"
                elif fcc.mode == "NONE":
                    tool_choice = "none"
                elif fcc.mode == "AUTO":
                    tool_choice = "auto"

            if gc.thinking_config:
                tc = gc.thinking_config
                if hasattr(tc, "thinking_level") and tc.thinking_level:
                    reasoning_effort = str(tc.thinking_level).split(".")[-1].lower()

        return OpenaiRequest(
            messages=messages,
            model=model_name,
            stream=isStream,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stop=stop,
            tools=openai_tools or None,
            tool_choice=tool_choice,
            response_format=response_format,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
            reasoning_effort=reasoning_effort,
            stream_options={"include_usage": True} if isStream else None,
        )
