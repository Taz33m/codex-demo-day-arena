#!/usr/bin/env python3
"""Prepare central owner briefs for standalone product repo rounds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from product_repos import ROUND_DIR, REPO_ROUNDS_DIR, ProductRepo, first_non_heading_lines, read_text, select_repos


STATUS_PATH = ROUND_DIR / "product_repo_status.json"
ALLOCATION_PATH = ROUND_DIR / "compute_allocation.json"


def load_status() -> dict[str, dict]:
    if not STATUS_PATH.exists():
        return {}
    rows = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    return {row["repo_name"]: row for row in rows}


def load_allocation() -> dict[str, dict]:
    if not ALLOCATION_PATH.exists():
        return {}
    rows = json.loads(ALLOCATION_PATH.read_text(encoding="utf-8"))
    return {row["repo_name"]: row for row in rows}


def repos_for_allocation(action: str) -> list[ProductRepo]:
    allocation = load_allocation()
    names = {name for name, row in allocation.items() if row.get("action") == action}
    return [repo for repo in select_repos(all_repos=True) if repo.repo_name in names]


def repos_by_ready_state(ready: bool) -> list[ProductRepo]:
    statuses = load_status()
    names = {name for name, row in statuses.items() if bool(row.get("ready")) is ready}
    return [repo for repo in select_repos(all_repos=True) if repo.repo_name in names]


def extra_round_context(repo: ProductRepo, round_name: str, allocation: dict[str, dict]) -> str:
    if round_name == "round-1":
        return ""
    round_label = round_name.replace("-", " ").title()
    buyer_review = read_text(ROUND_DIR / "buyer-usefulness" / repo.repo_name / "BUYER_USEFULNESS.md", limit=7000)
    next_request = read_text(repo.local_path / "NEXT_ROUND_REQUEST.md", limit=4000)
    outcome_files = sorted(repo.local_path.glob("ROUND_*_OUTCOME.md"), reverse=True)
    outcome_name = outcome_files[0].name if outcome_files else "ROUND_2_OUTCOME.md"
    round_outcome = read_text(outcome_files[0], limit=4500) if outcome_files else ""
    row = allocation.get(repo.repo_name, {})
    return f"""
## {round_label} Allocation Context

- Allocation action: `{row.get('action', 'unknown')}`
- Buyer score: `{row.get('buyer_score', 'unknown')}`
- Buyer verdict: `{row.get('buyer_verdict', 'unknown')}`
- Buyer recommendation: `{row.get('buyer_recommendation', 'unknown')}`
- Allocation reason: {row.get('reason', 'No allocation reason found.')}

This repo earned a funded owner slot. The round must change an investor belief, not merely add more code.

## Latest Round Outcome ({outcome_name})

```text
{round_outcome or 'No round outcome file found.'}
```

## Current Next-Round Request

```text
{next_request or 'No NEXT_ROUND_REQUEST.md found.'}
```

## Buyer Usefulness Review

```text
{buyer_review or 'No buyer usefulness review found.'}
```
"""


def brief_for(repo: ProductRepo, status: dict, round_name: str, allocation: dict[str, dict]) -> str:
    repo_dir = repo.local_path
    product_summary = "\n".join(first_non_heading_lines(read_text(repo_dir / "PRODUCT.md"), 6))
    customer_summary = "\n".join(first_non_heading_lines(read_text(repo_dir / "CUSTOMER.md"), 5))
    metrics = status.get("metrics", {})
    flags = status.get("flags", ["status_not_available"])
    taste_missing = metrics.get("taste_calibration_missing_items", [])
    live_taste_path = repo_dir / "TASTE_CALIBRATION.md"
    if not metrics.get("taste_calibration_exists") and live_taste_path.exists():
        taste_status = "present in repo; not yet reflected in validator snapshot"
    elif not metrics.get("taste_calibration_exists"):
        taste_status = "missing"
    elif taste_missing:
        taste_status = "incomplete: " + ", ".join(taste_missing)
    else:
        taste_status = "complete"
    top_logic = metrics.get("top_logic_files", [])
    top_logic_lines = "\n".join(f"- `{item['path']}`: {item['loc']} LOC" for item in top_logic) or "- Not available"
    commands = status.get("commands", [])
    command_lines = "\n".join(
        f"- `make {command['target']}`: {'pass' if command['passed'] else 'fail'}"
        for command in commands
    ) or "- Product contract has not been run from the standalone repo yet."

    round_label = "Round 1" if round_name == "round-1" else round_name.replace("-", " ").title()
    extra_context = extra_round_context(repo, round_name, allocation)
    return f"""# Owner Brief: {repo.product}

## Repo

- Team: `{repo.team}`
- Product repo: [{repo.repo_name}]({repo.url})
- Track: `{repo.track}`
- Local workspace: `{repo.local_path}`

## Current Product Summary

{product_summary or 'No product summary found.'}

## Current Customer Summary

{customer_summary or 'No customer summary found.'}

## Current Product Contract

{command_lines}

## Current Maturity Signals

- Logic LOC: `{metrics.get('logic_loc', 'unknown')}`
- Logic files: `{metrics.get('logic_file_count', 'unknown')}`
- Test/eval LOC: `{metrics.get('test_eval_loc', 'unknown')}`
- Product surface signal: `{metrics.get('has_product_surface_signal', 'unknown')}`
- Surface source files: `{', '.join(metrics.get('product_surface_source_files', [])) or 'none'}`
- Generated surface artifacts: `{', '.join(metrics.get('generated_product_surface_files', [])) or 'none'}`
- Receipt useful artifact signal: `{metrics.get('receipt_has_buyer_relevant_artifact', 'unknown')}`
- Taste Bank calibration: `{taste_status}`
- Flags: `{', '.join(flags) if flags else 'none'}`

Top implementation files:

{top_logic_lines}

{extra_context}

## {round_label} Mandate

This repo must move from prototype to investable product evidence.

Do not spend the round polishing narrative unless it directly maps to code, tests, evals, demo output, or receipt evidence.

Your job is not to make the repo "better." Your job is to make it more fundable.

For a funded follow-up round, your job is sharper: implement the smallest product/code/eval changes that could move this from "buyer-compelling" to "absolute investable." If the buyer review says the blocker is real data, ingestion, multi-case state, workflow adoption, sandbox credentials, or external validity, work there before adding surface polish.

Highest-level concerns for this round:

1. Before coding, write `TASTE_CALIBRATION.md` from `../../reference/TASTE_BANK_RUBRIC.md`, at least two exemplar profiles, and at least one anti-pattern. Borrow the bar, not the build.
2. If the repo is mostly a Python CLI, decide whether that is actually the buyer-relevant product surface. If not, add a small real local product/operator surface.
3. Increase product depth before video: richer workflow, better architecture, tougher evals, stronger generated artifacts.
4. Treat pivoting as allowed, but expensive. Pivot only if it creates a sharper company and rebuilds the product contract.
5. Preserve runnable commands: `make demo`, `make test`, `make eval`, `make receipt`.
6. Leave the repo comparison-ready against the other 19 startups.

You should not stop just because the repo improved. Clear the maturity flags above, or explain precisely why a remaining flag is the right tradeoff for the current investment decision.

Flag-specific guidance:

- `architecture_too_thin`: split large engines into meaningful source modules or add production-shaped internal boundaries.
- `no_buyer_relevant_product_surface_signal`: add maintainable source-controlled product surface code. Generated HTML/output alone does not clear this.
- `test_eval_depth_low`: add harder evals, negative cases, and measurable assertions.
- `logic_loc_below_seed_bar`: add real product behavior only; do not add filler.
- `receipt_lacks_buyer_relevant_artifact`: make `make receipt` prove the product produced something a real customer might value.
- `missing_investment_readiness_answer`: create `INVESTMENT_READINESS.md` and answer the gate with product evidence.

For every remaining maturity flag, use this exact tradeoff format:

- Remaining flag:
- Why it remains:
- Why fixing it was lower ROI than what we did:
- What investor belief would change if fixed:
- Would this block funding?
- Next exact patch:

## Pivot Guidance

Pivots are allowed when the current wedge is structurally weaker than a sharper adjacent wedge.

If you pivot, create `PIVOT_DECISION.md` and explain:

- old company,
- new company,
- why the pain is stronger,
- what evidence carries over,
- what evidence was rebuilt,
- why this increases the chance of a fictional $10M investment.

If you do not pivot, explicitly say so in `ROUND_STATUS.md`.

## Expected Owner Output

Update the repo itself, not the arena.

Required before finishing:

```bash
make demo
make test
make eval
make receipt
```

Create or update:

- `TASTE_CALIBRATION.md`
- `ROUND_STATUS.md`
- `PRODUCT_MATURITY.md`
- `INVESTMENT_READINESS.md`
- `NEXT_ROUND_REQUEST.md` if the repo asks for one more sprint
- `PIVOT_DECISION.md` only if pivoting

If the repo asks for another round, the next-round request must identify the funding delta: what an investor will believe after the next round that they do not believe now.

Final owner message should state whether this repo is now closer to an absolute `invest` recommendation.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--repo")
    parser.add_argument("--team")
    parser.add_argument("--track")
    parser.add_argument("--tier")
    parser.add_argument("--allocation-action")
    parser.add_argument("--not-ready", action="store_true", help="Select repos that failed the latest product repo validator.")
    parser.add_argument("--ready", action="store_true", help="Select repos that passed the latest product repo validator.")
    parser.add_argument("--round-name", default="round-1")
    args = parser.parse_args()

    if args.ready and args.not_ready:
        raise SystemExit("Use only one of --ready or --not-ready.")
    if args.allocation_action:
        repos = repos_for_allocation(args.allocation_action)
        if not repos:
            raise SystemExit(f"No repos matched allocation action: {args.allocation_action}")
    elif args.ready:
        repos = repos_by_ready_state(True)
    elif args.not_ready:
        repos = repos_by_ready_state(False)
    else:
        repos = select_repos(all_repos=args.all, repo_name=args.repo, team=args.team, track=args.track, tier=args.tier)
    statuses = load_status()
    allocation = load_allocation()
    round_dir = REPO_ROUNDS_DIR / args.round_name
    for repo in repos:
        repo_round_dir = round_dir / repo.repo_name
        repo_round_dir.mkdir(parents=True, exist_ok=True)
        (repo_round_dir / "logs").mkdir(parents=True, exist_ok=True)
        brief = brief_for(repo, statuses.get(repo.repo_name, {}), args.round_name, allocation)
        path = repo_round_dir / "OWNER_BRIEF.md"
        path.write_text(brief, encoding="utf-8")
        print(f"{repo.repo_name}: wrote {path.relative_to(ROUND_DIR.parent.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
