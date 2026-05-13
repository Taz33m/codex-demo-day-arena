#!/usr/bin/env python3
"""Run buyer-usefulness judges against structurally ready product repos."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import tempfile
from pathlib import Path

from product_repos import ROOT, ROUND_DIR, ProductRepo, read_text, select_repos


DEFAULT_MODEL = "gpt-5.5"
DEFAULT_REASONING = "xhigh"
DEFAULT_PROMPT = ROOT / "prompts" / "buyer-usefulness-judge.md"
BUYER_DIR = ROUND_DIR / "buyer-usefulness"
ALLOCATION_PATH = ROUND_DIR / "compute_allocation.json"


def probe_model(model: str, reasoning: str, timeout: int) -> None:
    with tempfile.NamedTemporaryFile(prefix="codex-buyer-judge-probe-", suffix=".txt", delete=False) as output:
        output_path = output.name
    try:
        proc = subprocess.run(
            [
                "codex",
                "exec",
                "--full-auto",
                "--ephemeral",
                "-m",
                model,
                "-c",
                f'model_reasoning_effort="{reasoning}"',
                "-o",
                output_path,
                "-",
            ],
            input="Say OK and nothing else.",
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        partial = exc.stdout if isinstance(exc.stdout, str) else ""
        raise SystemExit(
            "Model probe timed out. Refusing to launch buyer judges.\n"
            f"model={model} reasoning={reasoning} timeout={timeout}s\n"
            f"stdout_tail={partial[-2000:]}"
        ) from None
    output_text = read_text(Path(output_path)).strip()
    if proc.returncode != 0 or "OK" not in output_text:
        raise SystemExit(
            "Model probe failed. Refusing to launch buyer judges.\n"
            f"model={model} reasoning={reasoning} exit={proc.returncode}\n"
            f"last_message={output_text!r}\n"
            f"stdout_tail={proc.stdout[-2000:]}"
        )


def load_status() -> dict[str, dict]:
    status_path = ROUND_DIR / "product_repo_status.json"
    if not status_path.exists():
        raise SystemExit(f"Missing product status: {status_path}")
    rows = json.loads(status_path.read_text(encoding="utf-8"))
    return {row["repo_name"]: row for row in rows}


def ready_filter(repos: list[ProductRepo], statuses: dict[str, dict], ready_only: bool) -> list[ProductRepo]:
    if not ready_only:
        return repos
    return [repo for repo in repos if statuses.get(repo.repo_name, {}).get("ready")]


def allocation_repos(action: str) -> list[ProductRepo]:
    if not ALLOCATION_PATH.exists():
        raise SystemExit(f"Missing compute allocation: {ALLOCATION_PATH}")
    rows = json.loads(ALLOCATION_PATH.read_text(encoding="utf-8"))
    names = {row["repo_name"] for row in rows if row.get("action") == action}
    return [repo for repo in select_repos(all_repos=True) if repo.repo_name in names]


def artifact_excerpt(repo: ProductRepo, rel_path: str, limit: int = 3500) -> str:
    path = repo.local_path / rel_path
    if not path.exists() or not path.is_file():
        return ""
    text = read_text(path, limit=limit)
    return f"\n### {rel_path}\n\n```text\n{text}\n```\n"


def buyer_packet(repo: ProductRepo, status: dict) -> str:
    metrics = status.get("metrics", {})
    receipt_outputs = metrics.get("receipt_buyer_artifacts", [])
    excerpts = ""
    for rel_path in [
        "ROUND_2_OUTCOME.md",
        "TASTE_CALIBRATION.md",
        "INVESTMENT_READINESS.md",
        "PRODUCT.md",
        "CUSTOMER.md",
        "MOCKS.md",
        "ROUND_STATUS.md",
        "PRODUCT_MATURITY.md",
    ]:
        excerpts += artifact_excerpt(repo, rel_path, limit=4500)
    for rel_path in receipt_outputs[:4]:
        if rel_path.endswith((".md", ".json", ".html", ".csv")):
            excerpts += artifact_excerpt(repo, rel_path, limit=3000)
    return f"""# Buyer Packet: {repo.product}

- Repo: {repo.url}
- Track: {repo.track}
- Local path: {repo.local_path}
- Validator ready: {status.get('ready')}
- Validator flags: {', '.join(status.get('flags', [])) or 'none'}
- Logic LOC: {metrics.get('logic_loc')}
- Test/eval LOC: {metrics.get('test_eval_loc')}
- Product surface source files: {', '.join(metrics.get('product_surface_source_files', [])) or 'none'}
- Generated product surface files: {', '.join(metrics.get('generated_product_surface_files', [])) or 'none'}
- Receipt buyer artifacts: {', '.join(receipt_outputs) or 'none'}
- Investment readiness decision: {metrics.get('investment_readiness_decision')}

{excerpts}
"""


def parse_review(text: str) -> dict:
    verdict_match = re.search(
        r"\b(buyer_compelling|structurally_ready_but_commercially_weak|not_ready)\b",
        text,
        re.IGNORECASE,
    )
    score_match = re.search(r"\bscore\s*:?\s*(\d{1,3})\b", text, re.IGNORECASE)
    if not score_match:
        score_match = re.search(r"\*\*\s*(\d{1,3})\s*/\s*100\s*\*\*", text, re.IGNORECASE)
    if not score_match:
        score_match = re.search(r"\b(\d{1,3})\s*/\s*100\b", text, re.IGNORECASE)
    recommendation_match = re.search(r"\b(fund-more-compute|hold|pivot|archive)\b", text, re.IGNORECASE)
    score = int(score_match.group(1)) if score_match else None
    if score is not None:
        score = max(0, min(100, score))
    return {
        "score": score,
        "verdict": verdict_match.group(1).lower() if verdict_match else "unknown",
        "recommendation": recommendation_match.group(1).lower() if recommendation_match else "unknown",
    }


def reparse_existing(repos: list[ProductRepo]) -> list[dict]:
    results: list[dict] = []
    for repo in repos:
        output_path = BUYER_DIR / repo.repo_name / "BUYER_USEFULNESS.md"
        if not output_path.exists():
            continue
        text = read_text(output_path)
        parsed = parse_review(text)
        result = {
            "repo_name": repo.repo_name,
            "product": repo.product,
            "url": repo.url,
            "exit_code": 0,
            "output_path": str(output_path.relative_to(ROOT)),
            "run_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            **parsed,
        }
        (BUYER_DIR / repo.repo_name / "BUYER_USEFULNESS.json").write_text(
            json.dumps(result, indent=2) + "\n",
            encoding="utf-8",
        )
        print(
            f"{repo.repo_name}: reparsed verdict={result['verdict']} "
            f"score={result['score']} recommendation={result['recommendation']}"
        )
        results.append(result)
    return results


def run_judge(repo: ProductRepo, status: dict, model: str, reasoning: str, timeout: int, execute: bool) -> dict:
    out_dir = BUYER_DIR / repo.repo_name
    out_dir.mkdir(parents=True, exist_ok=True)
    packet = buyer_packet(repo, status)
    (out_dir / "BUYER_PACKET.md").write_text(packet, encoding="utf-8")
    prompt = read_text(DEFAULT_PROMPT) + "\n\n# Buyer Packet\n\n" + packet
    if not execute:
        print(f"{repo.repo_name}: would run buyer judge")
        return {
            "repo_name": repo.repo_name,
            "product": repo.product,
            "url": repo.url,
            "score": None,
            "verdict": "dry_run",
            "recommendation": "dry_run",
        }
    output_path = out_dir / "BUYER_USEFULNESS.md"
    proc = subprocess.run(
        [
            "codex",
            "exec",
            "--full-auto",
            "--ephemeral",
            "-m",
            model,
            "-c",
            f'model_reasoning_effort="{reasoning}"',
            "-o",
            str(output_path),
            prompt,
        ],
        cwd=repo.local_path,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=timeout,
    )
    text = read_text(output_path)
    parsed = parse_review(text)
    result = {
        "repo_name": repo.repo_name,
        "product": repo.product,
        "url": repo.url,
        "exit_code": proc.returncode,
        "output_path": str(output_path.relative_to(ROOT)),
        "run_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        **parsed,
    }
    (out_dir / "BUYER_USEFULNESS.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"{repo.repo_name}: verdict={result['verdict']} score={result['score']} recommendation={result['recommendation']}")
    return result


def write_summary(results: list[dict]) -> None:
    BUYER_DIR.mkdir(parents=True, exist_ok=True)
    (BUYER_DIR / "summary.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Buyer Usefulness Summary",
        "",
        "| Product | Repo | Score | Verdict | Recommendation |",
        "|---|---|---:|---|---|",
    ]
    for result in sorted(results, key=lambda item: (-(item.get("score") or 0), item["repo_name"])):
        lines.append(
            f"| {result['product']} | [{result['repo_name']}]({result['url']}) | "
            f"{result.get('score') if result.get('score') is not None else ''} | "
            f"{result['verdict']} | {result['recommendation']} |"
        )
    (BUYER_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def merge_with_existing_summary(results: list[dict]) -> list[dict]:
    summary_path = BUYER_DIR / "summary.json"
    if not summary_path.exists():
        return results
    existing = json.loads(summary_path.read_text(encoding="utf-8"))
    by_repo = {row["repo_name"]: row for row in existing}
    for row in results:
        by_repo[row["repo_name"]] = row
    return list(by_repo.values())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--repo")
    parser.add_argument("--team")
    parser.add_argument("--track")
    parser.add_argument("--tier")
    parser.add_argument("--allocation-action")
    parser.add_argument("--ready-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--reasoning", default=DEFAULT_REASONING)
    parser.add_argument("--probe-timeout", type=int, default=90)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--skip-model-check", action="store_true")
    parser.add_argument("--reparse-existing", action="store_true")
    parser.add_argument(
        "--merge-existing",
        action="store_true",
        help="Replace selected repos in the existing portfolio summary instead of writing a selected-only summary.",
    )
    args = parser.parse_args()

    if args.allocation_action:
        repos = allocation_repos(args.allocation_action)
    else:
        repos = select_repos(all_repos=args.all, repo_name=args.repo, team=args.team, track=args.track, tier=args.tier)
    statuses = load_status()
    repos = ready_filter(repos, statuses, args.ready_only)
    if not repos:
        raise SystemExit("No repos selected for buyer judging.")
    if args.reparse_existing:
        results = reparse_existing(repos)
        if not results:
            raise SystemExit("No existing buyer reviews found to reparse.")
        if args.merge_existing:
            results = merge_with_existing_summary(results)
        write_summary(results)
        return 0
    if args.execute and not args.skip_model_check:
        probe_model(args.model, args.reasoning, args.probe_timeout)
    results = [run_judge(repo, statuses.get(repo.repo_name, {}), args.model, args.reasoning, args.timeout, args.execute) for repo in repos]
    if args.merge_existing:
        results = merge_with_existing_summary(results)
    write_summary(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
