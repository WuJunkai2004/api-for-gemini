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

from server.schema.model.base import ClientRequest
from server.schema.request import APIRequest


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
    # For DeepSeek / reasoning models
    extra_body: Optional[dict[str, Any]] = None

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
                if not part.text:
                    print(part)
                    print("=" * 20)

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
                messages.append(
                    ChatCompletionAssistantMessageParam(
                        role="assistant", content="".join(texts), tool_calls=tools
                    )
                )
            if role == "user" and len(tools) > 0:
                raise RuntimeError("User message cannot contain tool calls")

        return OpenaiRequest(
            messages=messages,
            model=model_name,
            stream=isStream,
        )
