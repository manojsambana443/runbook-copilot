"""Evaluation harness. Measures retrieval hit-rate, answer accuracy, guardrail behaviour, latency and cost.

Usage:
    python -m eval.run_eval                       # full evaluation (needs OPENAI_API_KEY)
    python -m eval.run_eval --retrieval-only      # retrieval comparison only (cheap: embeddings only)
    python -m eval.run_eval --min-accuracy 0.8    # exit with code 1 if answer accuracy is below 80%
"""
import argparse
import json
import statistics
import sys
from pathlib import Path

import numpy as np

from app.config import Settings
from app.service import CopilotService

QUESTIONS = Path(__file__).parent / "questions.json"
RESULTS = Path(__file__).parent / "results.json"


def retrieval_eval(service: CopilotService, questions: list[dict], k: int) -> dict:
    answerable = [q for q in questions if q["type"] == "answerable"]
    report = {}
    for mode in ("vector", "bm25", "hybrid"):
        hits = 0
        for q in answerable:
            docs = service.retriever.search(
                q["question"], k=k, kind="runbook", mode=mode, unique_sources=True
            )
            hits += any(d.metadata["source"] == q["expected_doc"] for d in docs)
        report[mode] = round(hits / len(answerable), 3)
    return report


def end_to_end_eval(service: CopilotService, questions: list[dict]) -> dict:
    correct = total = 0
    adv_total = adv_refused = adv_unsafe = 0
    latencies, in_tok, out_tok, cost = [], 0, 0, 0.0
    failures = []

    for q in questions:
        res = service.ask(q["question"])
        latencies.append(res["latency_s"])
        in_tok += res["usage"]["input_tokens"]
        out_tok += res["usage"]["output_tokens"]
        cost += res["usage"]["est_cost_usd"]

        if q["type"] == "answerable":
            total += 1
            ok = res["status"] == "pending_approval" and res["fix_id"] == q["expected_fix"]
            correct += ok
            if not ok:
                failures.append({"id": q["id"], "question": q["question"], "got": res["fix_id"], "status": res["status"]})
        else:
            adv_total += 1
            if res["status"] == "pending_approval":
                adv_unsafe += 1
                failures.append({"id": q["id"], "question": q["question"], "got": res["fix_id"], "status": res["status"]})
            else:
                adv_refused += 1

    n = len(questions)
    return {
        "answer_accuracy": round(correct / total, 3),
        "answerable_questions": total,
        "adversarial_questions": adv_total,
        "adversarial_blocked": adv_refused,
        "adversarial_unsafe_proposals": adv_unsafe,
        "latency_p50_s": round(float(np.percentile(latencies, 50)), 2),
        "latency_p95_s": round(float(np.percentile(latencies, 95)), 2),
        "avg_cost_per_query_usd": round(cost / n, 5),
        "total_tokens": {"input": in_tok, "output": out_tok},
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retrieval-only", action="store_true")
    parser.add_argument("--min-accuracy", type=float, default=0.0)
    parser.add_argument("--k", type=int, default=3)
    args = parser.parse_args()

    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    settings = Settings()
    service = CopilotService(settings)
    service.cache = None  # measure real model calls, not cache hits

    report = {"questions": len(questions), "retrieval_hit_rate_at_k": retrieval_eval(service, questions, args.k)}
    print("Retrieval hit-rate@%d:" % args.k, report["retrieval_hit_rate_at_k"])

    if not args.retrieval_only:
        report["end_to_end"] = end_to_end_eval(service, questions)
        e2e = report["end_to_end"]
        print(f"Answer accuracy:      {e2e['answer_accuracy']:.1%} of {e2e['answerable_questions']}")
        print(f"Adversarial blocked:  {e2e['adversarial_blocked']}/{e2e['adversarial_questions']}")
        print(f"Latency p50 / p95:    {e2e['latency_p50_s']}s / {e2e['latency_p95_s']}s")
        print(f"Avg cost per query:   ${e2e['avg_cost_per_query_usd']}")
        for f in e2e["failures"]:
            print("  FAIL", f)

    RESULTS.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not args.retrieval_only and report["end_to_end"]["answer_accuracy"] < args.min_accuracy:
        print(f"Accuracy below the {args.min_accuracy:.0%} gate", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
