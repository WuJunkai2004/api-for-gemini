from google import genai

def test_request():
    client = genai.Client(
        api_key="fake-key",
        http_options={
            "base_url": "http://127.0.0.1:18000",
        }
    )
    
    model_id = "gemini-2.5-flash-lite"
    
    print(f"Sending request to {model_id}...")
    response = client.models.generate_content(
        model=model_id,
        contents="Say hello!"
    )
    
    print("Response received:")
    print(response.text)

if __name__ == "__main__":
    test_request()
