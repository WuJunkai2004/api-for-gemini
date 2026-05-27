from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api_for_gemini.server.api.generateContent import router as generate_content_router
from api_for_gemini.server.api.generateStreaming import router as generate_stream_router
from api_for_gemini.server.api.probe import router as probe_router
from api_for_gemini.server.api.status import router as status_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Grovider", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(generate_content_router, prefix="/v1beta/models")
app.include_router(generate_stream_router, prefix="/v1beta/models")
app.include_router(status_router)
app.include_router(probe_router)
