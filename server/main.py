import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# os.environ.clear()

from server.api.generateContent import router as generate_content_router
from server.api.probe import router as probe_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\033[H\033[J")
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
app.include_router(probe_router)
