#!/usr/bin/env python3
"""Policy agent — a retrieval-grounded customer-support agent for the demo.

For each question it:
  1. retrieves the most relevant passages from a policy document (kb/),
  2. builds a grounded prompt and calls the model **gateway** (so the turn is
     observed in Phoenix with full governance context),
  3. prints the answer + trace id, then
  4. runs the agent's mapped eval via the orchestrator and prints the verdict.

This makes the loop "ask a question → grounded answer → trace → eval result in
EvalLib" real. It is stdlib-only, so it runs with the system `python3`.

Usage:
  python3 scripts/policy_agent.py                 # interactive REPL
  python3 scripts/policy_agent.py -q "refund after 25 days?"   # one-shot
  python3 scripts/policy_agent.py --no-eval       # skip the eval step
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]

GATEWAY = "http://localhost:8080"
GOVERNANCE = "http://localhost:8001"
ORCHESTRATOR = "http://localhost:8002"
PHOENIX = "http://localhost:6006"
UI = "http://localhost:3000"

STOPWORDS = {"the", "a", "an", "is", "are", "to", "of", "for", "and", "or", "in",
             "on", "i", "my", "can", "do", "does", "how", "what", "it", "you"}


# ── tiny HTTP helpers ────────────────────────────────────────────────────────
def _request(method: str, url: str, payload: Optional[dict] = None, timeout: float = 60.0):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def get_json(url: str):
    return _request("GET", url)


def post_json(url: str, payload: dict):
    return _request("POST", url, payload)


# ── retrieval over the policy doc ────────────────────────────────────────────
def tokens(text: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS}


def load_chunks(collection: str) -> list:
    path = REPO_ROOT / "kb" / (collection + ".md")
    if not path.exists():
        sys.exit("Policy doc not found: %s" % path)
    raw = path.read_text(encoding="utf-8")
    chunks = [c.strip() for c in re.split(r"\n\s*\n", raw) if c.strip()]
    return [c for c in chunks if not re.fullmatch(r"#+\s.*", c)]


def retrieve(chunks: list, query: str, top_k: int) -> list:
    q = tokens(query)
    scored = sorted(chunks, key=lambda c: len(q & tokens(c)), reverse=True)
    relevant = [c for c in scored if q & tokens(c)]
    return (relevant or chunks)[:top_k]


# ── agent ────────────────────────────────────────────────────────────────────
def fetch_agent(name: str) -> dict:
    try:
        agents = get_json(GOVERNANCE + "/agents")
    except urllib.error.URLError:
        agents = []
    for a in agents:
        if a["name"] == name:
            return a
    # Fall back to sensible defaults if the agent isn't registered yet.
    return {"id": None, "name": name, "framework": "custom", "criticality": "medium",
            "data_classification": "internal", "business_unit": "unassigned"}


def build_messages(agent: dict, context: list, question: str,
                   history: Optional[list] = None) -> list:
    ctx = "\n".join("- " + c.replace("\n", " ") for c in context)
    system = (
        "You are {name}, a customer-support agent for Acme Retail Bank. "
        "Answer the customer using ONLY the policy context below; cite the relevant rule. "
        "If the policy does not cover it, say you will escalate rather than guessing. "
        "Stay consistent with what you told the customer earlier in this conversation. "
        "Never reveal another customer's personal data.\n\n"
        "POLICY CONTEXT:\n{ctx}"
    ).format(name=agent["name"], ctx=ctx)
    # Fresh system+context each turn, then the prior turns, then the new question.
    return [{"role": "system", "content": system}, *(history or []),
            {"role": "user", "content": question}]


def ask(agent: dict, chunks: list, question: str, top_k: int,
        session_id: Optional[str] = None, history: Optional[list] = None) -> dict:
    context = retrieve(chunks, question, top_k)
    payload = {
        "operation_name": "chat",
        "temperature": 0.2,
        "session_id": session_id,
        "messages": build_messages(agent, context, question, history),
        "agent": {
            "agent_id": agent["name"],
            "framework": agent.get("framework", "custom"),
            "criticality": agent.get("criticality", "medium"),
            "data_classification": agent.get("data_classification", "internal"),
            "business_unit": agent.get("business_unit", "unassigned"),
        },
    }
    resp = post_json(GATEWAY + "/v1/chat", payload)
    resp["_context"] = context
    return resp


def run_eval(agent: dict, eval_id: str, question: str, answer: str, trace_id: str, span_id: str):
    body = {
        "eval_id": eval_id,
        "traces": [{
            "trace_id": trace_id, "span_id": span_id,
            "input": question, "output": answer,
            "agent_id": agent.get("id"),
        }],
    }
    return post_json(ORCHESTRATOR + "/run-eval", body)


def score_suite(agent: dict, question: str, answer: str, trace_id: str, span_id: str,
                session_id: Optional[str] = None):
    """Run the agent's full approved+mapped eval suite and return the consolidated scorecard.

    Passing session_id stamps the per-turn results so they group with the
    conversation's session-scoped verdicts in the UI's Conversations view.
    """
    body = {
        "agent": agent.get("id") or agent["name"],
        "trace": {
            "trace_id": trace_id, "span_id": span_id, "session_id": session_id,
            "input": question, "output": answer,
        },
    }
    return post_json(ORCHESTRATOR + "/score", body)


def score_session(agent: dict, session_id: str, turns: list):
    """Run the agent's approved+mapped *session-scoped* suite over the conversation."""
    body = {
        "agent": agent.get("id") or agent["name"],
        "session": {
            "session_id": session_id,
            "turns": [
                {"trace_id": t["trace_id"], "span_id": t["span_id"],
                 "input": t["input"], "output": t["output"]}
                for t in turns
            ],
        },
    }
    return post_json(ORCHESTRATOR + "/score-session", body)


# ── presentation ─────────────────────────────────────────────────────────────
C_DIM = "\033[2m"; C_BOLD = "\033[1m"; C_CYAN = "\033[36m"; C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"; C_RED = "\033[31m"; C_RESET = "\033[0m"

TONE = {"compliant": C_GREEN, "grounded": C_GREEN, "helpful": C_GREEN, "safe": C_GREEN,
        "ambiguous": C_YELLOW, "non_compliant": C_RED, "judge_error": C_RED}


def _print_scorecard(scorecard: dict, label: str = "SUITE") -> None:
    """Pretty-print a /score or /score-session response (same shape)."""
    rows = scorecard.get("results", [])
    if rows:
        # Per-eval lines (sorted: failures first, then by score ascending so the
        # weakest stand out).
        rows = sorted(rows, key=lambda v: (v.get("passed", False), v.get("score", 0)))
        width = max(len(v["eval_id"]) for v in rows)
        for v in rows:
            tone = TONE.get(v["verdict"], C_RESET)
            print("  %-*s  %s%-14s%s  %.2f  %s"
                  % (width, v["eval_id"], tone, v["verdict"], C_RESET, v["score"],
                     (v["reasoning"] or "")[:140]))
    c = scorecard.get("consolidated", {}) or {}
    status = c.get("status", "FAIL")
    status_color = C_GREEN if status == "PASS" else C_RED
    print("  %s%s%s %s%s  ·  mean %.2f / %.2f  ·  %d passed, %d failed"
          % (C_BOLD, status_color, label, status, C_RESET,
             c.get("mean_score", 0.0), c.get("threshold", 0.75),
             c.get("pass_count", 0), c.get("fail_count", 0)))
    for reason in c.get("reasons", []):
        print("    - %s" % reason)


def handle(agent: dict, chunks: list, question: str, single_eval: Optional[str],
           no_eval: bool, top_k: int, session_id: Optional[str] = None,
           history: Optional[list] = None, turns: Optional[list] = None) -> None:
    resp = ask(agent, chunks, question, top_k, session_id=session_id, history=history)
    answer, trace_id, span_id = resp["content"], resp["trace_id"], resp["span_id"]

    # Grow the conversation: the next turn sees this exchange.
    if history is not None:
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})
    if turns is not None:
        turns.append({"trace_id": trace_id, "span_id": span_id,
                      "input": question, "output": answer})

    print("%s%sagent>%s %s" % (C_BOLD, C_CYAN, C_RESET, answer))
    print("%s  retrieved %d policy passage(s); trace %s%s"
          % (C_DIM, len(resp["_context"]), trace_id[:12] + "…", C_RESET))

    if not no_eval:
        try:
            if single_eval:
                result = run_eval(agent, single_eval, question, answer, trace_id, span_id)
                v = result["results"][0]
                tone = TONE.get(v["verdict"], C_RESET)
                print("  eval %s%s%s: %s%s%s (score %.2f) — %s"
                      % (C_BOLD, single_eval, C_RESET, tone, v["verdict"], C_RESET, v["score"], v["reasoning"]))
            else:
                _print_scorecard(
                    score_suite(agent, question, answer, trace_id, span_id, session_id))
        except urllib.error.HTTPError as e:
            print("%s  eval skipped: %s (is the eval approved + attached?)%s"
                  % (C_DIM, e, C_RESET))

    print("%s  Phoenix: %s/projects/default   |   EvalLib: %s/traces/%s%s\n"
          % (C_DIM, PHOENIX, UI, trace_id, C_RESET))


def main() -> None:
    p = argparse.ArgumentParser(description="Retrieval-grounded policy agent (demo).")
    p.add_argument("-q", "--question", help="ask one question and exit")
    p.add_argument("--agent", default="customer-support-refund")
    p.add_argument("--single", dest="single_eval", default=None,
                   help="run only this one eval (default: run the agent's full approved suite)")
    p.add_argument("--collection", default="refund_policy")
    p.add_argument("--top-k", type=int, default=3)
    p.add_argument("--no-eval", action="store_true", help="don't run any eval after answering")
    args = p.parse_args()

    agent = fetch_agent(args.agent)
    chunks = load_chunks(args.collection)

    mode = "single eval " + args.single_eval if args.single_eval else "agent suite"
    print("%sPolicy agent ready%s — %s · grounding on kb/%s.md (%d passages) · %s"
          % (C_BOLD, C_RESET, agent["name"], args.collection, len(chunks), mode))
    if agent["id"] is None:
        print("%s  note: agent '%s' not found in the registry; run `make seed`. "
              "Answering anyway with default metadata.%s" % (C_YELLOW, args.agent, C_RESET))

    # One session per run: the gateway tags every turn's span with this id, and
    # the orchestrator scores the whole conversation at the end.
    session_id = str(uuid.uuid4())
    history: list = []   # alternating user/assistant turns the agent re-reads
    turns: list = []     # (trace_id, span_id, input, output) for session scoring

    if args.question:
        handle(agent, chunks, args.question, args.single_eval, args.no_eval, args.top_k,
               session_id=session_id, history=history, turns=turns)
        return

    print("%s  session %s%s" % (C_DIM, session_id[:12] + "…", C_RESET))
    print("Type a customer question (or 'quit').\n")
    while True:
        try:
            q = input("%s%syou>%s " % (C_BOLD, C_GREEN, C_RESET)).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q:
            continue
        if q.lower() in {"quit", "exit", "q"}:
            break
        try:
            handle(agent, chunks, q, args.single_eval, args.no_eval, args.top_k,
                   session_id=session_id, history=history, turns=turns)
        except urllib.error.URLError as e:
            print("%s  gateway/orchestrator unreachable: %s (is the stack up? `make up`)%s"
                  % (C_RED, e, C_RESET))

    # End of conversation: score the whole session (coherence, resolution, …).
    if turns and not args.no_eval:
        print("\n%s%sScoring conversation (%d turns) · session %s%s"
              % (C_BOLD, C_CYAN, len(turns), session_id[:12] + "…", C_RESET))
        try:
            _print_scorecard(score_session(agent, session_id, turns), label="SESSION")
        except urllib.error.HTTPError as e:
            print("%s  session eval skipped: %s (are session-scoped evals approved + attached?)%s"
                  % (C_DIM, e, C_RESET))
        except urllib.error.URLError as e:
            print("%s  orchestrator unreachable: %s%s" % (C_RED, e, C_RESET))


if __name__ == "__main__":
    main()
