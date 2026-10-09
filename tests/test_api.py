"""API tests with a stub service, so no OpenAI key is needed."""
from fastapi.testclient import TestClient

import app.main as main


class StubService:
    def ask(self, question, logs=None):
        return {"id": "abc123", "status": "pending_approval", "fix_id": "FIX-003", "question": question}

    def approve(self, pid):
        if pid == "abc123":
            return {"id": pid, "status": "approved", "fix_id": "FIX-003"}
        return None

    def reload(self):
        return {"chunks": 1, "fixes": 1}


def test_endpoints(monkeypatch):
    monkeypatch.setattr(main, "CopilotService", StubService)
    with TestClient(main.app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.post("/ask", json={"question": "pods at high cpu"}).json()["fix_id"] == "FIX-003"
        assert client.post("/ask", json={"question": "x"}).status_code == 422  # too short
        assert client.post("/approve/abc123").json()["status"] == "approved"
        assert client.post("/approve/nope").status_code == 404
        assert client.post("/ingest").json()["chunks"] == 1
        assert "copilot_requests_total" in client.get("/metrics/").text or client.get("/metrics").status_code in (200, 307)
