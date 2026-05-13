#!/usr/bin/env python3
"""Validate standalone product repos and score their repo maturity signals."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from product_repos import ROUND_DIR, ProductRepo, select_repos


TARGETS = ["demo", "test", "eval", "receipt"]
CODE_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css"}
LOGIC_EXT = {".py", ".js", ".ts", ".tsx", ".jsx"}
SKIP_PARTS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    ".venv",
    "venv",
    "out",
    "output",
    "outputs",
    "evidence",
    "logs",
    "video",
}

SURFACE_SOURCE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"<html",
        r"<body",
        r"fastapi|flask|streamlit|gradio",
        r"http\.server|BaseHTTPRequestHandler",
        r"dashboard|cockpit|workspace|artifact viewer|review queue|decision cockpit",
        r"render_[a-z0-9_]*html|html_escape|text/html",
    ]
]

BUYER_ARTIFACT_KEYWORDS = [
    "memo",
    "report",
    "packet",
    "workspace",
    "dashboard",
    "cockpit",
    "universe",
    "worksheet",
    "plan",
    "brief",
    "triage",
    "diligence",
    "audit",
    "review",
    "scorecard",
    "action",
    "pricing",
    "launch",
    "parent",
    "buyer",
]

KNOWN_EXEMPLARS = {
    "citadail": ["citadail"],
    "rpinsight": ["rpinsight", "rpinsights", "rp insight", "rp insights"],
    "narrativedesk": ["narrativedesk", "narrative desk"],
    "marketmind-q": ["marketmind-q", "marketmind", "mktmind", "mktmind-qtm"],
}

ANTI_PATTERNS = [
    "script-with-report",
    "generic-ai-dashboard",
    "docs-without-product",
    "pretty-but-not-useful",
]


def run_make(repo: ProductRepo, target: str, timeout: int) -> dict:
    try:
        proc = subprocess.run(
            ["make", target],
            cwd=repo.local_path,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout,
        )
        return {
            "target": target,
            "passed": proc.returncode == 0,
            "exit_code": proc.returncode,
            "output_tail": "\n".join(proc.stdout.splitlines()[-20:]),
        }
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout if isinstance(exc.stdout, str) else ""
        return {
            "target": target,
            "passed": False,
            "exit_code": "timeout",
            "output_tail": "\n".join(output.splitlines()[-20:]),
        }


def include(path: Path) -> bool:
    return not any(part in SKIP_PARTS for part in path.parts)


def line_count(path: Path) -> int:
    try:
        return sum(1 for _ in path.open("r", encoding="utf-8", errors="ignore"))
    except OSError:
        return 0


def text_matches_surface(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return any(pattern.search(text) for pattern in SURFACE_SOURCE_PATTERNS)


def generated_surface_files(repo: ProductRepo) -> list[Path]:
    candidates: list[Path] = []
    for dirname in ("app/out", "app/output", "app/outputs", "evidence"):
        base = repo.local_path / dirname
        if not base.exists():
            continue
        candidates.extend(path for path in base.rglob("*") if path.is_file() and path.suffix in {".html", ".htm"})
    return sorted(candidates)


def receipt_metrics(repo: ProductRepo) -> dict:
    receipt_path = repo.local_path / "evidence" / "demo_receipt.json"
    if not receipt_path.exists():
        return {
            "receipt_exists": False,
            "receipt_has_buyer_relevant_artifact": False,
            "receipt_generated_outputs": [],
            "receipt_buyer_artifacts": [],
        }
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "receipt_exists": True,
            "receipt_has_buyer_relevant_artifact": False,
            "receipt_generated_outputs": [],
            "receipt_buyer_artifacts": [],
            "receipt_error": "invalid_json",
        }
    outputs = [str(item) for item in receipt.get("generated_outputs", [])]
    buyer_artifacts = []
    for output in outputs:
        lower = output.lower()
        if "eval" in lower and not any(keyword in lower for keyword in ("report", "packet", "review", "workspace")):
            continue
        if any(keyword in lower for keyword in BUYER_ARTIFACT_KEYWORDS):
            buyer_artifacts.append(output)
    return {
        "receipt_exists": True,
        "receipt_has_buyer_relevant_artifact": bool(buyer_artifacts),
        "receipt_generated_outputs": outputs[:30],
        "receipt_buyer_artifacts": buyer_artifacts[:30],
    }


def investment_readiness_metrics(repo: ProductRepo) -> dict:
    path = repo.local_path / "INVESTMENT_READINESS.md"
    text = ""
    if path.exists():
        text = path.read_text(encoding="utf-8", errors="ignore")
    required_terms = [
        "customer",
        "pain",
        "wedge",
        "product surface",
        "core output",
        "aha",
        "differentiation",
        "technical depth",
        "evaluation",
        "receipt",
    ]
    missing = [term for term in required_terms if term not in text.lower()]
    decision_match = re.search(
        r"\b(investable|ready|needs one more sprint|needs one more unblock sprint|pivot|kill|hold|archive)\b",
        text,
        re.IGNORECASE,
    )
    return {
        "investment_readiness_exists": path.exists(),
        "investment_readiness_missing_terms": missing,
        "investment_readiness_decision": decision_match.group(1).lower() if decision_match else None,
    }


def taste_calibration_metrics(repo: ProductRepo) -> dict:
    path = repo.local_path / "TASTE_CALIBRATION.md"
    text = ""
    if path.exists():
        text = path.read_text(encoding="utf-8", errors="ignore")
    lower = text.lower()
    exemplar_refs = [
        exemplar
        for exemplar, aliases in KNOWN_EXEMPLARS.items()
        if any(alias in lower for alias in aliases)
    ]
    anti_pattern_refs = [
        slug
        for slug in ANTI_PATTERNS
        if slug in lower or slug.replace("-", " ") in lower
    ]
    checks = {
        "relevant_exemplars_referenced": bool(exemplar_refs),
        "standards_borrowed": "standard" in lower and "borrow" in lower,
        "anti_pattern_identified": bool(anti_pattern_refs) or "anti-pattern" in lower or "anti pattern" in lower,
        "product_aha_moment_defined": "aha" in lower,
        "what_not_to_copy_stated": "not to copy" in lower or "not copy" in lower or "do not copy" in lower,
    }
    missing = [name for name, passed in checks.items() if not passed]
    return {
        "taste_calibration_exists": path.exists(),
        "taste_calibration_referenced_exemplars": exemplar_refs,
        "taste_calibration_referenced_anti_patterns": anti_pattern_refs,
        "taste_calibration_missing_items": missing,
    }


def metrics(repo: ProductRepo) -> dict:
    files = [path for path in repo.local_path.rglob("*") if path.is_file() and include(path)]
    logic_files = [path for path in files if path.suffix in LOGIC_EXT]
    code_files = [path for path in files if path.suffix in CODE_EXT]
    test_eval_files = [
        path
        for path in files
        if path.suffix in LOGIC_EXT and ("test" in path.name.lower() or "eval" in path.name.lower())
    ]
    product_surface_source_files = [
        path
        for path in files
        if path.name not in {"receipt.py"}
        and "test" not in path.name.lower()
        and "eval" not in path.name.lower()
        and (
            path.suffix in {".html", ".css", ".tsx", ".jsx"}
            or path.name in {"server.py", "app.py", "main.py"}
            or "ui" in path.name.lower()
            or "surface" in path.name.lower()
            or "dashboard" in path.name.lower()
            or "cockpit" in path.name.lower()
            or (path.suffix in CODE_EXT and text_matches_surface(path))
        )
    ]
    generated_surfaces = generated_surface_files(repo)
    top_logic = sorted(
        ((line_count(path), str(path.relative_to(repo.local_path))) for path in logic_files),
        reverse=True,
    )[:5]
    receipt = receipt_metrics(repo)
    investment_readiness = investment_readiness_metrics(repo)
    taste_calibration = taste_calibration_metrics(repo)
    return {
        "logic_loc": sum(line_count(path) for path in logic_files),
        "code_loc": sum(line_count(path) for path in code_files),
        "test_eval_loc": sum(line_count(path) for path in test_eval_files),
        "logic_file_count": len(logic_files),
        "code_file_count": len(code_files),
        "has_product_surface_signal": bool(product_surface_source_files) and bool(generated_surfaces),
        "product_surface_source_files": [str(path.relative_to(repo.local_path)) for path in product_surface_source_files[:12]],
        "generated_product_surface_files": [str(path.relative_to(repo.local_path)) for path in generated_surfaces[:12]],
        "top_logic_files": [{"path": path, "loc": loc} for loc, path in top_logic],
        **receipt,
        **investment_readiness,
        **taste_calibration,
    }


def maturity_warnings(repo_metrics: dict) -> list[str]:
    warnings: list[str] = []
    missing_taste = repo_metrics.get("taste_calibration_missing_items") or []
    if missing_taste:
        warnings.append(f"taste_calibration_incomplete:{','.join(missing_taste)}")
    return warnings


def maturity_flags(repo_metrics: dict, commands: list[dict], funded: bool = False) -> list[str]:
    flags: list[str] = []
    if not all(command["passed"] for command in commands):
        flags.append("product_contract_not_green")
    if repo_metrics["logic_loc"] < 1200:
        flags.append("logic_loc_below_seed_bar")
    if repo_metrics["test_eval_loc"] < 300:
        flags.append("test_eval_depth_low")
    if repo_metrics["logic_file_count"] < 6:
        flags.append("architecture_too_thin")
    if not repo_metrics["has_product_surface_signal"]:
        flags.append("no_buyer_relevant_product_surface_signal")
    if not repo_metrics.get("receipt_has_buyer_relevant_artifact"):
        flags.append("receipt_lacks_buyer_relevant_artifact")
    if (
        not repo_metrics.get("investment_readiness_exists")
        or repo_metrics.get("investment_readiness_missing_terms")
        or not repo_metrics.get("investment_readiness_decision")
    ):
        flags.append("missing_investment_readiness_answer")
    if funded and repo_metrics.get("taste_calibration_missing_items"):
        flags.append("missing_taste_calibration")
    return flags


def validate(repo: ProductRepo, timeout: int, funded: bool = False) -> dict:
    if not (repo.local_path / ".git").exists():
        return {
            "repo_name": repo.repo_name,
            "team": repo.team,
            "product": repo.product,
            "track": repo.track,
            "local_path": str(repo.local_path),
            "ready": False,
            "flags": ["repo_not_synced"],
            "warnings": [],
            "commands": [],
            "metrics": {},
        }
    commands = [run_make(repo, target, timeout) for target in TARGETS]
    repo_metrics = metrics(repo)
    flags = maturity_flags(repo_metrics, commands, funded=funded)
    warnings = maturity_warnings(repo_metrics)
    return {
        "repo_name": repo.repo_name,
        "team": repo.team,
        "product": repo.product,
        "track": repo.track,
        "url": repo.url,
        "local_path": str(repo.local_path),
        "ready": not flags,
        "flags": flags,
        "warnings": warnings,
        "commands": commands,
        "metrics": repo_metrics,
    }


def write_outputs(results: list[dict], merge: bool = True) -> list[dict]:
    ROUND_DIR.mkdir(parents=True, exist_ok=True)
    output_path = ROUND_DIR / "product_repo_status.json"
    if merge and output_path.exists():
        existing = json.loads(output_path.read_text(encoding="utf-8"))
        by_repo = {row["repo_name"]: row for row in existing}
        for result in results:
            by_repo[result["repo_name"]] = result
        merged = list(by_repo.values())
        merged.sort(key=lambda row: row["repo_name"])
    else:
        merged = results
    output_path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Product Repo Status",
        "",
        "| Repo | Product | Contract | Surface | Receipt Artifact | Taste | Logic LOC | Test/Eval LOC | Flags | Warnings |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for result in merged:
        contract = "pass" if all(command.get("passed") for command in result["commands"]) else "fail"
        metrics = result.get("metrics", {})
        flags = ", ".join(result["flags"]) if result["flags"] else "none"
        warnings = ", ".join(result.get("warnings", [])) if result.get("warnings") else "none"
        surface = "yes" if metrics.get("has_product_surface_signal") else "no"
        receipt = "yes" if metrics.get("receipt_has_buyer_relevant_artifact") else "no"
        if not metrics.get("taste_calibration_exists"):
            taste = "missing"
        elif metrics.get("taste_calibration_missing_items"):
            taste = "incomplete"
        else:
            taste = "yes"
        lines.append(
            f"| [{result['repo_name']}]({result.get('url', '')}) | {result['product']} | {contract} | {surface} | {receipt} | {taste} | "
            f"{metrics.get('logic_loc', 0)} | {metrics.get('test_eval_loc', 0)} | {flags} | {warnings} |"
        )
    (ROUND_DIR / "product_repo_status.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--repo")
    parser.add_argument("--team")
    parser.add_argument("--track")
    parser.add_argument("--tier")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument(
        "--funded",
        action="store_true",
        help="Make Taste Bank calibration a hard maturity flag for funded sprints.",
    )
    args = parser.parse_args()

    repos = select_repos(all_repos=args.all, repo_name=args.repo, team=args.team, track=args.track, tier=args.tier)
    results = [validate(repo, args.timeout, funded=args.funded) for repo in repos]
    write_outputs(results)
    for result in results:
        flags = ", ".join(result["flags"]) if result["flags"] else "none"
        warnings = ", ".join(result.get("warnings", [])) if result.get("warnings") else "none"
        print(f"{result['repo_name']}: ready={result['ready']} flags={flags} warnings={warnings}")
    return 0 if all(result["ready"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
