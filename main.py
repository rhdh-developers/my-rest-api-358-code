from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from pokeapi import router as pokeapi_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(
        base_url="https://pokeapi.co/api/v2", timeout=10.0
    )
    yield
    await app.state.http_client.aclose()


app = FastAPI(
    title="my-rest-api-358",
    description="FastAPI REST API service scaffolded by RHDH",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(pokeapi_router)


@app.get("/api/v1/hello")
def hello():
    return {"message": "hello world", "service": "my-rest-api-358"}

@app.get("/api/v1/goodbye")
def bye():
    return {"message": "goodbye world", "service": "my-rest-api-358"}



@app.get("/health")
def health():
    return {"status": "ok"}
