import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api_for_gemini.server.main:app",
        host="0.0.0.0",
        port=18000,
        reload=True,
        reload_dirs=["api_for_gemini/server"],
    )
