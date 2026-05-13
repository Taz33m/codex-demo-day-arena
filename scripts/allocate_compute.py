#!/usr/bin/env python3
"""Allocate the next owner round from validator and buyer-usefulness results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from product_repos import ROUND_DIR, ProductRepo, read_text, select_repos


BUYER_DIR = ROUND_DIR / "buyer-usefulness"
OUTPUT_JSON = ROUND_DIR / "compute_allocation.json"
OUTPUT_MD = ROUND_DIR / "compute_allocation.md"


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def external_proof_blocker(repo: ProductRepo | None) -> str | None:
    if repo is None:
        return None
    paths = [
        "ROUND_5_OUTCOME.md",
        "ROUND_4_OUTCOME.md",
        "ROUND_3_OUTCOME.md",
        "ROUND_2_OUTCOME.md",
        "NEXT_ROUND_REQUEST.md",
        "INVESTMENT_READINESS.md",
    ]
    text = "\n".join(read_text(repo.local_path / path, limit=5000) for path in paths).lower()
    proof_terms = (
        "sandbox credential",
        "sandbox credentials",
        "buyer-owned",
        "real customer",
        "real agreement",
        "real agreements",
        "anonymized real",
        "customer export",
        "real tutor",
        "real school",
        "design partner",
        "design-partner",
        "counsel-reviewed",
        "historical tickets",
        "historical batch",
        "historical batches",
        "permissioned historical",
        "licensed historical",
        "licensed feed",
        "external proof",
        "external validation",
        "external validity",
        "external-validity",
        "provider export",
        "real provider",
        "real files",
        "customer-provided",
        "real recruiter",
        "real founder",
        "real founders",
        "external-founder",
        "founder-owned",
        "founder launch-note",
        "founder launch notes",
        "own launch notes",
        "own launch materials",
        "real launch",
        "real launch packs",
        "real batch",
        "real batches",
        "hedge-fund analyst",
        "analyst review",
        "analyst edit",
        "live ats",
        "ats sandbox",
        "sandbox ats",
        "actual parser",
        "actual pdf",
        "actual docx",
        "real banker",
        "redacted banker",
        "banker evidence",
        "banker-built",
        "banker label",
        "banker labels",
        "banker work product",
        "real md",
        "real md decision",
        "real md decisions",
        "real buyer universe",
        "real buyer universes",
        "redacted prior",
        "redacted prior-process",
        "prior-process evidence",
        "real-data shadow-pilot",
        "redacted real close",
        "real close export",
        "real close exports",
        "real cfo",
        "real prep-time",
        "real prep time",
    )
    gate_terms = (
        "more compute is justified only",
        "more compute only",
        "one more compute round only if",
        "more compute for external",
        "should receive more compute only",
        "request one external-validation sprint",
        "fund one external-founder proof",
        "fund one more sprint only if",
        "fund one more round if",
        "funded only if",
        "only if real",
        "only if credential",
        "only for real",
        "should not be granted without",
        "waiting on buyer-owned",
        "waiting on real",
        "until it proves",
        "not investable without real",
        "not yet investable until",
        "still not investable until",
        "not investable until",
        "not an absolute invest recommendation",
        "next round cannot secure real",
        "next funding delta should",
        "next round must replace fixtures",
        "real founder adoption is unproven",
        "more compute without external proof",
        "fund more compute only if",
        "fund one focused",
        "should not receive another product-polish round",
        "should be held",
        "commercial proof remains synthetic",
        "all commercial proof remains synthetic",
    )
    if any(gate in text for gate in gate_terms) and any(term in text for term in proof_terms):
        return "Latest repo outcome says the next funded step requires external buyer data, sandbox credentials, or live proof."
    return None


def allocation_reason(
    row: dict,
    status: dict,
    eligible_rank: int | None,
    funded_count: int,
    external_blocker: str | None,
) -> tuple[str, str]:
    if not status.get("ready"):
        return "salvage-or-pivot", "Validator is not green; normal owner compute is blocked."
    if row.get("verdict") != "buyer_compelling":
        return "hold", "Structurally ready but not buyer-compelling."
    if external_blocker:
        return "external-proof-required", external_blocker
    if row.get("recommendation") != "fund-more-compute":
        return "hold", f"Buyer judge recommendation is `{row.get('recommendation', 'unknown')}`."
    if row.get("score") is None:
        return "hold", "Buyer score was not parsed; allocation requires a numeric score."
    if eligible_rank is not None and eligible_rank <= funded_count:
        return "round-2-owner", f"Top-{funded_count} buyer-compelling repo by score."
    return "hold", f"Buyer-compelling, but outside the top-{funded_count} funded set for this round."


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--funded-count", type=int, default=3)
    args = parser.parse_args()

    buyer_rows = load_json(BUYER_DIR / "summary.json", [])
    status_rows = load_json(ROUND_DIR / "product_repo_status.json", [])
    statuses = {row["repo_name"]: row for row in status_rows}
    repos = {repo.repo_name: repo for repo in select_repos(all_repos=True)}

    ranked = sorted(
        buyer_rows,
        key=lambda row: (
            -(row.get("score") or -1),
            0 if row.get("recommendation") == "fund-more-compute" else 1,
            row["repo_name"],
        ),
    )
    rank_by_repo = {row["repo_name"]: index for index, row in enumerate(ranked, start=1)}
    blocker_by_repo = {name: external_proof_blocker(repos.get(name)) for name in rank_by_repo}
    eligible_rows = [
        row
        for row in ranked
        if statuses.get(row["repo_name"], {}).get("ready")
        and not blocker_by_repo.get(row["repo_name"])
        and row.get("verdict") == "buyer_compelling"
        and row.get("recommendation") == "fund-more-compute"
        and row.get("score") is not None
    ]
    eligible_rank_by_repo = {row["repo_name"]: index for index, row in enumerate(eligible_rows, start=1)}

    allocations = []
    for row in ranked:
        status = statuses.get(row["repo_name"], {})
        action, reason = allocation_reason(
            row,
            status,
            eligible_rank_by_repo.get(row["repo_name"]),
            args.funded_count,
            blocker_by_repo.get(row["repo_name"]),
        )
        allocations.append(
            {
                "rank": rank_by_repo[row["repo_name"]],
                "repo_name": row["repo_name"],
                "product": row["product"],
                "url": row["url"],
                "validator_ready": bool(status.get("ready")),
                "buyer_score": row.get("score"),
                "buyer_verdict": row.get("verdict"),
                "buyer_recommendation": row.get("recommendation"),
                "action": action,
                "reason": reason,
            }
        )

    OUTPUT_JSON.write_text(json.dumps(allocations, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Compute Allocation",
        "",
        "Only fundable products receive more compute. This allocation uses the maturity validator plus the buyer-usefulness judge.",
        "",
        f"Round 2 owner slots: {args.funded_count}",
        "",
        "| Rank | Product | Repo | Ready | Buyer Score | Verdict | Recommendation | Action | Reason |",
        "|---:|---|---|---:|---:|---|---|---|---|",
    ]
    for row in allocations:
        ready = "yes" if row["validator_ready"] else "no"
        score = "" if row["buyer_score"] is None else str(row["buyer_score"])
        lines.append(
            f"| {row['rank']} | {row['product']} | [{row['repo_name']}]({row['url']}) | {ready} | {score} | "
            f"{row['buyer_verdict']} | {row['buyer_recommendation']} | {row['action']} | {row['reason']} |"
        )
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for row in allocations:
        print(f"{row['rank']}. {row['repo_name']}: {row['action']} score={row['buyer_score']} reason={row['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
