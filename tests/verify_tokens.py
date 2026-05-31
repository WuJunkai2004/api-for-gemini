import json
import time

import httpx

# 默认测试配置
# 注意：运行此测试需要本地服务已开启并在 18000 端口监听
BASE_URL = "http://127.0.0.1:18000/v1beta/models"
MODEL = "qwen"

# 为了触发缓存，我们需要一段足够长的文本。
LONG_CONTEXT = (
    "Answer next number for the sequence of numbers to acknowledge receipt: "
    + " ".join([str(i) for i in range(500)])
)


def verify_usage_metadata(usage: dict, context: str):
    """验证 usageMetadata 字段是否包含必要的统计项"""
    print(f"\nVerifying usageMetadata for {context}:")
    # print(json.dumps(usage, indent=2))

    assert "promptTokenCount" in usage, f"Missing promptTokenCount in {context}"
    assert "candidatesTokenCount" in usage, f"Missing candidatesTokenCount in {context}"
    assert "totalTokenCount" in usage, f"Missing totalTokenCount in {context}"
    assert "cachedContentTokenCount" in usage, (
        f"Missing cachedContentTokenCount in {context}"
    )

    cached = usage.get("cachedContentTokenCount", 0)
    print(f"  - Prompt: {usage.get('promptTokenCount')}")
    print(f"  - Cached: {cached}")
    print(f"  - Candidates: {usage.get('candidatesTokenCount')}")
    print(f"  - Total: {usage.get('totalTokenCount')}")

    return cached


def test_token_caching_logic():
    """通过连续两次请求来验证缓存逻辑是否生效"""
    url_sync = f"{BASE_URL}/{MODEL}:generateContent"
    url_stream = f"{BASE_URL}/{MODEL}:streamGenerateContent"

    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": LONG_CONTEXT}]},
            {"role": "user", "parts": [{"text": "Now, tell me a short joke."}]},
        ]
    }

    print("--- Step 1: Initial Request (Cold Start) ---")
    resp1 = httpx.post(url_sync, json=payload, timeout=60.0)
    assert resp1.status_code == 200
    usage1 = resp1.json()["usageMetadata"]
    verify_usage_metadata(usage1, "Initial Sync Request")

    # 等待一小会儿确保缓存写入（部分后端可能需要时间）
    print("\nWaiting for cache to settle...")
    time.sleep(2)

    print("\n--- Step 2: Second Request (Expecting Cache Hit) ---")
    # 稍微修改一下最后的问题，但保持前缀一致
    payload["contents"][-1]["parts"][0]["text"] = "Now, tell me a different short joke."

    resp2 = httpx.post(url_sync, json=payload, timeout=60.0)
    assert resp2.status_code == 200
    usage2 = resp2.json()["usageMetadata"]
    cached_sync = verify_usage_metadata(usage2, "Second Sync Request")

    if cached_sync > 0:
        print("\n✅ Success: Non-streaming cache hit detected!")
    else:
        print(
            "\n⚠️ Warning: No non-streaming cache hit detected. (This depends on the backend provider's policy)"
        )

    print("\n--- Step 3: Streaming Request (Expecting Cache Hit) ---")
    payload["contents"][-1]["parts"][0]["text"] = "Finally, tell me one more cat joke."

    last_chunk = None
    with httpx.stream("POST", url_stream, json=payload, timeout=60.0) as resp3:
        assert resp3.status_code == 200
        for line in resp3.iter_lines():
            if line.startswith("data: "):
                last_chunk = json.loads(line[6:])

    assert last_chunk is not None
    usage3 = last_chunk["usageMetadata"]
    cached_stream = verify_usage_metadata(usage3, "Streaming Request Final Chunk")

    if cached_stream > 0:
        print("\n✅ Success: Streaming cache hit detected!")
    else:
        print("\n⚠️ Warning: No streaming cache hit detected.")


if __name__ == "__main__":
    print(f"Starting Token Caching Verification Tests for model: {MODEL}...")
    try:
        test_token_caching_logic()
        print("\nVerification process completed.")
    except Exception as e:
        print(f"\nTests failed: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
