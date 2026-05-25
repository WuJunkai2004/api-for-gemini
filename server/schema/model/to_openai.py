from server.schema.request import GoogleRequest


def transfer(req: GoogleRequest, target_model: str, isStream: bool):
    messages = []

    # 1. 处理 System Instruction
    if req.system_instruction and req.system_instruction.parts:
        # 提取系统提示词文本
        sys_text = "".join([p.text for p in req.system_instruction.parts if p.text])
        if sys_text:
            messages.append({"role": "system", "content": sys_text})

    # 2. 处理多轮对话历史 (Contents)
    for content in req.contents:
        # 角色映射：Gemini 的 'model' 对应 OpenAI 的 'assistant'
        role = "assistant" if content.role == "model" else "user"

        if not content.parts:
            continue  # 跳过没有内容的对话轮次

        # 提取并拼接文本 (MVP 阶段假设为纯文本交互)
        text_content = "".join([p.text for p in content.parts if p.text])

        if text_content:
            messages.append({"role": role, "content": text_content})

    # 3. 构造 OpenAI 的基础请求参数
    openai_kwargs = {
        "model": target_model,
        "messages": messages,
    }

    # 4. 处理生成配置 (Generation Config)
    if req.generation_config:
        config = req.generation_config

        if config.temperature is not None:
            openai_kwargs["temperature"] = config.temperature

        if config.top_p is not None:
            openai_kwargs["top_p"] = config.top_p

        if config.max_output_tokens is not None:
            openai_kwargs["max_tokens"] = config.max_output_tokens

        # 强制 JSON 输出模式
        if config.response_mime_type == "application/json":
            openai_kwargs["response_format"] = {"type": "json_object"}

    return openai_kwargs
