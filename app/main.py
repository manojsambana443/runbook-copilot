"""FastAPI entrypoint."""
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from prometheus_client import make_asgi_app
from pydantic import BaseModel, Field

from .service import CopilotService


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    logs: Optional[str] = Field(default=None, max_length=20000)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.service = CopilotService()
    yield


app = FastAPI(title="Runbook Copilot", version="1.0.0", lifespan=lifespan)
app.mount("/metrics", make_asgi_app())


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask")
def ask(req: AskRequest):
    return app.state.service.ask(req.question, req.logs)


@app.post("/approve/{proposal_id}")
def approve(proposal_id: str):
    result = app.state.service.approve(proposal_id)
    if result is None:
        raise HTTPException(status_code=404, detail="proposal not found")
    if "error" in result:
        raise HTTPException(status_code=409, detail=result["error"])
    return result


@app.post("/ingest")
def ingest():
    return app.state.service.reload()
