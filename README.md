# Runbook Copilot

A RAG + agentic assistant for on-call engineers. Paste an alert or log snippet; it retrieves the relevant
runbooks and past incidents, an agent reasons over them, and it proposes **one fix from an approved list**,
with citations. A human approves before anything happens. The service never executes fixes itself.

**Stack:** Python, FastAPI, LangChain, OpenAI API, hybrid retrieval (vector + BM25), Docker, Kubernetes (AKS),
Helm, Terraform, GitHub Actions, Prometheus.

## Architecture

```
 Alert / question (+ optional logs)
            |
        FastAPI  /ask
            |
   semantic cache --hit--> cached answer (no LLM call)
            | miss
     LangChain tool-using agent  --tools-->  search_runbooks     (hybrid retrieval: vector + BM25 + RRF)
            |                                search_past_incidents
            |                                triage_logs          (dedupe repeated log lines)
            |                                list_approved_fixes
            v
      structured proposal (answer, fix_id, confidence, citations)
            |
   guardrails: 1) fix_id in approved list  2) supporting runbook was actually retrieved  3) confidence >= threshold
            |
   pending_approval  /  escalated (to a human)  /  refused  ->  POST /approve/{id}
            |
   Prometheus metrics (/metrics): latency, tokens, cache hits, guardrail blocks
```

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # add your OPENAI_API_KEY, then: export $(grep -v '^#' .env | xargs)

python -m pytest -q             # offline tests, no API key needed
uvicorn app.main:app --reload   # http://localhost:8000/docs
```

```bash
curl -s localhost:8000/ask -H 'content-type: application/json' \
  -d '{"question":"Pods are at 95% CPU and the HPA is at max replicas"}' | python -m json.tool
curl -s -X POST localhost:8000/approve/<id-from-response>
```

## Evaluation

`eval/questions.json` holds 24 answerable questions (each with the expected runbook and fix) and 8 adversarial
ones (prompt injection, out-of-scope, unsafe or invented fixes).

```bash
python -m eval.run_eval --retrieval-only    # vector vs BM25 vs hybrid hit-rate@3 (embeddings only, very cheap)
python -m eval.run_eval --min-accuracy 0.8  # full run; exits non-zero below 80% accuracy (used as the CI gate)
```

Results are written to `eval/results.json`. Add your own questions to grow the set.

### Results (fill in from your own run)

| Metric | Value |
|---|---|
| Retrieval hit-rate@3: vector only | _run the eval_ |
| Retrieval hit-rate@3: BM25 only | _run the eval_ |
| Retrieval hit-rate@3: hybrid | _run the eval_ |
| Answer accuracy (answerable questions) | _run the eval_ |
| Adversarial queries blocked | _run the eval_ |
| p50 / p95 latency | _run the eval_ |
| Average cost per query | _run the eval_ |

### What the guardrails do

- **Allow-list:** the model may only name a fix ID that exists in `data/approved_fixes.json`.
- **Grounding:** the runbook that supports that fix must have been retrieved in the same run.
- **Confidence:** below `MIN_CONFIDENCE` the case is escalated to a human instead of guessed.
- Escalated and refused responses never carry a `fix_id`.

## Deploy to AKS

1. **Infrastructure** (Terraform): `cd terraform && terraform init && terraform apply -var suffix=<unique>`
   creates a resource group, ACR, and a one-node Free-tier AKS cluster with the AcrPull role.
2. **Image:** `az acr build -r <acr> -t runbook-copilot:v1 .`
3. **Secret:** `kubectl create secret generic openai-api-key --from-literal=OPENAI_API_KEY=<key>`
4. **Release:** `helm upgrade --install runbook-copilot helm/runbook-copilot --set image.repository=<acr>.azurecr.io/runbook-copilot --set image.tag=v1`
5. **Try it:** `kubectl port-forward svc/runbook-copilot 8000:80`

The pod exposes Prometheus metrics at `/metrics/` and carries scrape annotations.

CI (`.github/workflows/ci.yml`): tests + Gitleaks + Docker build on every push; the eval gate runs on `main`
when the `OPENAI_API_KEY` secret is set; deployment is a manual run that uses Azure OIDC login.

## Limitations (be honest about these)

- The knowledge base is a small synthetic set of 10 runbooks and 6 past incidents.
- The vector index is in memory and rebuilt on startup (fine at this size; use a managed vector DB at scale).
- Proposals and the semantic cache are in memory, so they reset on restart and are per-replica.
- Approval is recorded, not executed. Wiring it to real automation needs auth and audit logging.

## Project layout

```
app/        FastAPI service, agent, tools, guardrails, retriever, cache, metrics
data/       runbooks, past incidents, approved_fixes.json
eval/       evaluation questions and harness
tests/      offline tests (fake LLM and embeddings, no API calls)
helm/       Helm chart        terraform/  AKS + ACR        .github/  CI/CD
```
