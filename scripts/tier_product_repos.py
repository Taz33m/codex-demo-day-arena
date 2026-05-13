#!/usr/bin/env python3
"""Rank standalone product repos into portfolio compute tiers."""

from __future__ import annotations

import argparse
import json

from product_repos import ROUND_DIR


STATUS_PATH = ROUND_DIR / "product_repo_status.json"


HARD_FAIL_FLAGS = {
    "repo_not_synced",
    "product_contract_not_green",
    "receipt_lacks_buyer_relevant_artifact",
}


def contract_passed(row: dict) -> bool:
    return bool(row.get("commands")) and all(command.get("passed") for command in row["commands"])


def tier_for(row: dict) -> tuple[str, str]:
    flags = set(row.get("flags", []))
    metrics = row.get("metrics", {})
    if flags & HARD_FAIL_FLAGS or not contract_passed(row):
        return "tier-4-archive-or-merge", "Hard gate failure or no useful artifact."
    if not flags:
        return "tier-1-near-fundable", "Clears current maturity validator."
    if flags <= {"missing_investment_readiness_answer"}:
        return "tier-1-near-fundable", "Only missing investment-readiness packaging."
    if metrics.get("logic_loc", 0) >= 1200 and metrics.get("receipt_has_buyer_relevant_artifact"):
        if "no_buyer_relevant_product_surface_signal" in flags or "missing_investment_readiness_answer" in flags:
            return "tier-2-engine-needs-surface", "Has product engine/evidence but needs buyer-facing surface or readiness answer."
    if len(flags) <= 3 and metrics.get("receipt_has_buyer_relevant_artifact"):
        return "tier-2-engine-needs-surface", "Limited gaps; one focused owner round may clear them."
    return "tier-3-pivot-or-salvage", "Multiple maturity gaps; more compute needs a strong salvage or pivot thesis."


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", default=str(STATUS_PATH))
    args = parser.parse_args()

    rows = json.load(open(args.status, encoding="utf-8"))
    tiered = []
    for row in rows:
        tier, reason = tier_for(row)
        tiered.append(
            {
                "repo_name": row["repo_name"],
                "product": row["product"],
                "track": row["track"],
                "url": row.get("url", ""),
                "tier": tier,
                "reason": reason,
                "flags": row.get("flags", []),
                "decision": row.get("metrics", {}).get("investment_readiness_decision"),
            }
        )
    tiered.sort(key=lambda item: (item["tier"], item["track"], item["repo_name"]))

    ROUND_DIR.mkdir(parents=True, exist_ok=True)
    (ROUND_DIR / "portfolio_tiers.json").write_text(json.dumps(tiered, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Portfolio Compute Tiers",
        "",
        "Only fundable products receive more compute.",
        "",
        "| Tier | Product | Repo | Reason | Flags |",
        "|---|---|---|---|---|",
    ]
    for item in tiered:
        flags = ", ".join(item["flags"]) if item["flags"] else "none"
        lines.append(
            f"| {item['tier']} | {item['product']} | [{item['repo_name']}]({item['url']}) | "
            f"{item['reason']} | {flags} |"
        )
    (ROUND_DIR / "portfolio_tiers.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    counts: dict[str, int] = {}
    for item in tiered:
        counts[item["tier"]] = counts.get(item["tier"], 0) + 1
    for tier, count in sorted(counts.items()):
        print(f"{tier}: {count}")
    print(f"Wrote {ROUND_DIR / 'portfolio_tiers.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
