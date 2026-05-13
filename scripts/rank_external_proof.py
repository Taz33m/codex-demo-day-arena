#!/usr/bin/env python3
"""Rank product repos by external proof feasibility and write proof plans."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from product_repos import REPO_ROUNDS_DIR, ROUND_DIR, ProductRepo, load_product_repos


OUTPUT_DIR = REPO_ROUNDS_DIR / "external-proof"
OUTPUT_JSON = OUTPUT_DIR / "proof_priority.json"
OUTPUT_MD = OUTPUT_DIR / "PROOF_PRIORITY_REPORT.md"
PROOF_PLAN_DIR = OUTPUT_DIR / "proof-plans"


FACTOR_OVERRIDES: dict[str, dict] = {
    "wedgewise": {
        "reachable_customer_access": 9,
        "available_real_sample_data": 8,
        "demo_clarity": 9,
        "willingness_to_pay_signal": 7,
        "integration_complexity": 2,
        "compliance_data_sensitivity": 4,
        "target_buyer": "pre-seed and seed B2B founders with recent customer interview transcripts",
        "required_input": "3-5 real or anonymized customer interviews from one founder plus their current ICP notes",
        "fastest_method": "Founder interview plus manual upload of redacted transcripts into the local demo.",
        "success_signal": "Founder says the ICP memo is accurate enough to use in positioning, customer discovery, or investor prep and asks to run more interviews.",
        "failure_signal": "Founder says the memo is generic, misses their wedge, or would not change their next customer-discovery action.",
        "outreach_script": "I have a local product that turns messy customer interviews into an ICP decision memo and evidence-backed wedge. If you send 3 anonymized interview notes, I will return the memo and you can tell me whether it is useful or generic.",
        "demo_asset": "app/out/operator_console.html, app/out/icp_memo.md, app/out/founder_pack/external_proof_packet.md",
    },
    "canonkit-launch": {
        "reachable_customer_access": 9,
        "available_real_sample_data": 9,
        "demo_clarity": 8,
        "willingness_to_pay_signal": 6,
        "integration_complexity": 1,
        "compliance_data_sensitivity": 2,
        "target_buyer": "technical pre-seed founders preparing a first launch",
        "required_input": "real launch notes, draft landing copy, target persona notes, pricing notes, and proof claims",
        "fastest_method": "Use one founder's actual launch materials and return a claim ledger plus launch pack.",
        "success_signal": "Founder uses or edits the launch pack for a real landing page, launch email, or investor update.",
        "failure_signal": "Founder treats the output as generic copy and does not use any artifact.",
        "outreach_script": "Send me your messy launch notes and proof claims. I will run them through a local launch-pack generator and return the copy, checklist, and claim ledger so you can judge whether it saves real launch work.",
        "demo_asset": "generated launch pack, claim ledger, and receipt artifacts from make demo/make receipt",
    },
    "proofpulse": {
        "reachable_customer_access": 9,
        "available_real_sample_data": 8,
        "demo_clarity": 8,
        "willingness_to_pay_signal": 7,
        "integration_complexity": 2,
        "compliance_data_sensitivity": 4,
        "target_buyer": "pre-seed founders sending investor updates during an active fundraise",
        "required_input": "one real founder update draft plus screenshots, metrics notes, customer proof, or receipts",
        "fastest_method": "Run one founder's messy update notes through the product and ask whether the output is sendable to investors.",
        "success_signal": "Founder says the output is sendable with light edits or asks to use it for the next update cycle.",
        "failure_signal": "Founder says it adds narrative polish but does not improve trust, clarity, or investor follow-up.",
        "outreach_script": "If you have a messy investor update draft and a few receipts, I can return an evidence-backed update with routed asks. The only question: would you actually send or edit this?",
        "demo_asset": "investor update packet, evidence index, routed asks, and demo receipt",
    },
    "preppilot-tutor": {
        "reachable_customer_access": 8,
        "available_real_sample_data": 8,
        "demo_clarity": 8,
        "willingness_to_pay_signal": 6,
        "integration_complexity": 2,
        "compliance_data_sensitivity": 4,
        "target_buyer": "independent test-prep tutors and small tutoring centers",
        "required_input": "one real worksheet, student misses, tutoring notes, or anonymized recent session plan",
        "fastest_method": "Ask a tutor for an anonymized worksheet/session and return a prep packet plus review proof.",
        "success_signal": "Tutor says they would use the generated prep packet in an upcoming session or asks for another student case.",
        "failure_signal": "Tutor says the material is too generic, too hard to trust, or not aligned with their teaching workflow.",
        "outreach_script": "Send one anonymized worksheet or recent session note. I will return a tutor-ready prep packet and you can mark what you would keep, rewrite, or discard.",
        "demo_asset": "pilot proof packet, tutor review decisions, retained-vs-rewritten sections, prep-time savings",
    },
    "signaldraft-earnings-memo": {
        "reachable_customer_access": 5,
        "available_real_sample_data": 9,
        "demo_clarity": 8,
        "willingness_to_pay_signal": 7,
        "integration_complexity": 3,
        "compliance_data_sensitivity": 3,
        "target_buyer": "long/short equity analysts and PMs reviewing earnings events",
        "required_input": "public earnings transcript, press release, 10-Q, guidance table, and consensus snapshot",
        "fastest_method": "Run a recent public earnings event and send the generated memo to one finance operator for usefulness review.",
        "success_signal": "Analyst says the memo saves time, catches key variance/event issues, or would be edited into their research workflow.",
        "failure_signal": "Analyst says it is a generic summary and misses the actual debate or risk/reward question.",
        "outreach_script": "I ran a public earnings packet through a local memo generator. Would you spend five minutes telling me whether this is useful research workflow output or just summary theater?",
        "demo_asset": "generated earnings memo, source intake audit, eval results, demo receipt",
    },
    "signalprice": {
        "reachable_customer_access": 8,
        "available_real_sample_data": 7,
        "demo_clarity": 8,
        "willingness_to_pay_signal": 7,
        "integration_complexity": 3,
        "compliance_data_sensitivity": 5,
        "target_buyer": "seed and Series A B2B founders considering pricing changes",
        "required_input": "3-5 anonymized buyer-call excerpts plus current pricing notes",
        "fastest_method": "Run one founder's anonymized pricing call snippets and ask if the pricing test pack changes their next experiment.",
        "success_signal": "Founder asks to run more calls or uses the test pack in a pricing discussion.",
        "failure_signal": "Founder says it repeats obvious objections without creating a concrete test.",
        "outreach_script": "If you send anonymized buyer-call snippets and current pricing, I will return a pricing test pack. The useful/not-useful bar is whether it changes your next pricing experiment.",
        "demo_asset": "pilot evidence packet, pricing test pack, founder decision summary",
    },
    "misconceptionos": {
        "reachable_customer_access": 7,
        "available_real_sample_data": 7,
        "demo_clarity": 8,
        "willingness_to_pay_signal": 6,
        "integration_complexity": 3,
        "compliance_data_sensitivity": 5,
        "target_buyer": "AP/STEM tutors and learning-center academic managers",
        "required_input": "anonymized student answers over at least two sessions",
        "fastest_method": "Run one real anonymized student packet and ask whether the misconception trend is useful.",
        "success_signal": "Tutor uses the weekly diagnostic or asks to track another student.",
        "failure_signal": "Tutor says the diagnosis is obvious or not actionable.",
        "outreach_script": "Send anonymized student misses from two sessions. I will return a misconception trend packet and you can judge whether it would change tutoring.",
        "demo_asset": "weekly diagnostic packet and longitudinal tutor report",
    },
    "mentorbrief": {
        "reachable_customer_access": 7,
        "available_real_sample_data": 7,
        "demo_clarity": 7,
        "willingness_to_pay_signal": 6,
        "integration_complexity": 3,
        "compliance_data_sensitivity": 4,
        "target_buyer": "accelerator mentors and founder-program operators",
        "required_input": "real cohort notes, founder updates, or mentor meeting history",
        "fastest_method": "Ask one mentor/operator to provide anonymized cohort notes and review the generated brief.",
        "success_signal": "Mentor says the brief would improve a real founder meeting or reduce prep time.",
        "failure_signal": "Mentor says it is generic and misses the founder-specific next conversation.",
        "outreach_script": "Send anonymized founder notes from a recent mentoring cycle. I will return a prep brief and you can mark what you would use in the next meeting.",
        "demo_asset": "mentor prep brief, cohort proof packet, repeat-use metrics",
    },
    "reteachkit": {
        "reachable_customer_access": 7,
        "available_real_sample_data": 7,
        "demo_clarity": 8,
        "willingness_to_pay_signal": 5,
        "integration_complexity": 3,
        "compliance_data_sensitivity": 5,
        "target_buyer": "teachers and academic coaches with reteach planning responsibility",
        "required_input": "anonymized quiz misses, standard/unit, and class-level misconception notes",
        "fastest_method": "Run one anonymized class/quiz export and ask if the reteach plan is usable.",
        "success_signal": "Teacher says they would use the plan or worksheet in class.",
        "failure_signal": "Teacher says it is too generic or misaligned with classroom constraints.",
        "outreach_script": "Send an anonymized recent quiz export. I will return a reteach plan and worksheet, and you can tell me what survives your classroom judgment.",
        "demo_asset": "coach workspace, reteach plan, worksheet, receipt",
    },
    "sessionproof": {
        "reachable_customer_access": 7,
        "available_real_sample_data": 6,
        "demo_clarity": 8,
        "willingness_to_pay_signal": 7,
        "integration_complexity": 4,
        "compliance_data_sensitivity": 6,
        "target_buyer": "small tutoring-center owners and managers",
        "required_input": "anonymized session notes, quick-check scores, and parent communication examples",
        "fastest_method": "Ask one tutoring center/operator for anonymized sessions and return a parent/renewal packet.",
        "success_signal": "Manager says the packet would go to a parent or renewal conversation with light edits.",
        "failure_signal": "Manager says the packet is not trustworthy enough for parent communication.",
        "outreach_script": "Send anonymized recent tutoring notes and quick-check scores. I will return a renewal-ready progress packet and you can judge if it is parent-sendable.",
        "demo_asset": "manager renewal queue, parent progress packet, stale approval checks",
    },
    "reqtrace-diligence": {
        "reachable_customer_access": 5,
        "available_real_sample_data": 5,
        "demo_clarity": 8,
        "willingness_to_pay_signal": 7,
        "integration_complexity": 5,
        "compliance_data_sensitivity": 5,
        "requires_customer_data": True,
        "target_buyer": "agency owners and product leads responsible for implementation signoff",
        "required_input": "real PRD, tickets, shipped diff, and acceptance evidence from one delivery cycle",
        "fastest_method": "Run one redacted project pack and ask the operator whether the diligence report would have caught false-DONE risk.",
        "success_signal": "Operator says the report would change a release decision or client acceptance meeting.",
        "failure_signal": "Operator says the packet duplicates manual QA without improving judgment.",
        "outreach_script": "Send one redacted PRD/ticket/shipped-change pack. I will return a trace diligence report and you can tell me whether it would catch real delivery risk.",
        "demo_asset": "diligence report, reviewer acceptance summary, false-DONE risk packet",
    },
    "covenantlens": {
        "reachable_customer_access": 4,
        "available_real_sample_data": 7,
        "demo_clarity": 7,
        "willingness_to_pay_signal": 8,
        "integration_complexity": 5,
        "compliance_data_sensitivity": 6,
        "target_buyer": "private credit analysts and deal teams reviewing loan agreements",
        "required_input": "public or permissioned credit agreement plus analyst markup baseline",
        "fastest_method": "Run a public SEC exhibit agreement and ask one credit operator if the map/diff is credible.",
        "success_signal": "Analyst says the covenant map would save review time or catch negotiation issues.",
        "failure_signal": "Analyst says citation accuracy or nuance is insufficient for credit work.",
        "outreach_script": "I ran a public credit agreement through a covenant map/diff workflow. Can you tell me whether the output would survive a real underwriting review?",
        "demo_asset": "covenant map, diff, negotiation questions, technical receipt",
    },
    "boardbrief-fpa": {
        "reachable_customer_access": 5,
        "available_real_sample_data": 3,
        "demo_clarity": 8,
        "willingness_to_pay_signal": 8,
        "integration_complexity": 4,
        "compliance_data_sensitivity": 8,
        "requires_customer_data": True,
        "target_buyer": "first CFOs and Heads of Finance at Series A-C SaaS companies",
        "required_input": "redacted real close export, owner notes, final CFO memo edits, and prep-time baseline",
        "fastest_method": "Warm intro to a CFO willing to share a redacted prior close pack.",
        "success_signal": "CFO says the generated board narrative would enter a CEO pre-read or board draft with light edits.",
        "failure_signal": "CFO will not share data or says trust/accounting nuance blocks use.",
        "outreach_script": "If you can share a redacted prior close export and final memo, I can run a local tool and return the variance narrative plus edit-distance proof. The bar is whether you would use the memo.",
        "demo_asset": "CFO review workspace and design-partner validation packet",
    },
    "closeplan-map": {
        "reachable_customer_access": 5,
        "available_real_sample_data": 3,
        "demo_clarity": 8,
        "willingness_to_pay_signal": 7,
        "integration_complexity": 7,
        "compliance_data_sensitivity": 7,
        "requires_customer_data": True,
        "target_buyer": "B2B sales leaders running mutual action plans for active opportunities",
        "required_input": "real call transcript or notes plus CRM opportunity snapshot",
        "fastest_method": "Warm sales-operator proof with a redacted current or recently closed opportunity.",
        "success_signal": "Sales leader says the MAP would be used with a customer or forecast review.",
        "failure_signal": "Data access/integration is too hard or the MAP does not improve deal control.",
        "outreach_script": "Share a redacted call transcript and CRM stage snapshot. I will return a mutual action plan and you can judge whether it changes deal execution.",
        "demo_asset": "buyer-facing MAP, CRM reconciliation, receipt",
    },
    "evidencehire": {
        "reachable_customer_access": 5,
        "available_real_sample_data": 3,
        "demo_clarity": 8,
        "willingness_to_pay_signal": 6,
        "integration_complexity": 6,
        "compliance_data_sensitivity": 9,
        "requires_customer_data": True,
        "target_buyer": "recruiting leads handling hiring-scorecard consistency",
        "required_input": "redacted ATS notes, interview feedback, and hiring decision evidence",
        "fastest_method": "Permissioned recruiter sandbox or heavily redacted past hiring packet.",
        "success_signal": "Recruiter says the evidence packet would change a hiring debrief or reduce bias/coordination work.",
        "failure_signal": "PII/compliance or ATS access blocks proof.",
        "outreach_script": "If you can provide a redacted hiring packet, I will return an evidence-backed scorecard packet and you can judge if it would improve debrief quality.",
        "demo_asset": "ATS-style evidence packet and dry-run ATS export",
    },
    "evidencerail-soc2": {
        "reachable_customer_access": 5,
        "available_real_sample_data": 3,
        "demo_clarity": 8,
        "willingness_to_pay_signal": 7,
        "integration_complexity": 6,
        "compliance_data_sensitivity": 8,
        "requires_customer_data": True,
        "target_buyer": "security/compliance operators preparing SOC 2 evidence",
        "required_input": "redacted SOC 2 evidence export, control list, auditor requests, and ticket history",
        "fastest_method": "Warm security operator willing to run a redacted evidence snapshot.",
        "success_signal": "Operator says the packet would reduce audit prep or auditor follow-up.",
        "failure_signal": "Trust/compliance concerns block sharing or output is not audit-credible.",
        "outreach_script": "Share a redacted SOC 2 evidence snapshot and control list. I will return an evidence rail packet and you can judge if it would survive audit prep.",
        "demo_asset": "evidence snapshot comparison and dry-run ticket handoff",
    },
    "triagekit": {
        "reachable_customer_access": 4,
        "available_real_sample_data": 4,
        "demo_clarity": 8,
        "willingness_to_pay_signal": 7,
        "integration_complexity": 7,
        "compliance_data_sensitivity": 7,
        "requires_customer_data": True,
        "target_buyer": "support ops leaders and CX managers with repetitive ticket triage",
        "required_input": "redacted historical tickets, macros/runbooks, and resolution labels",
        "fastest_method": "Customer export or public sample ticket set with operator review.",
        "success_signal": "Operator says triage/routing would reduce handle time or improve SLA risk.",
        "failure_signal": "Output is generic routing without real policy/runbook lift.",
        "outreach_script": "Share redacted historical support tickets plus macros. I will return a triage packet and you can judge whether it would save agent time.",
        "demo_asset": "triage packet, runbook match, receipt",
    },
    "policypilot-it": {
        "reachable_customer_access": 4,
        "available_real_sample_data": 3,
        "demo_clarity": 8,
        "willingness_to_pay_signal": 7,
        "integration_complexity": 8,
        "compliance_data_sensitivity": 8,
        "requires_customer_data": True,
        "target_buyer": "IT/security admins reviewing access requests",
        "required_input": "redacted access tickets, policy rules, identity attributes, and approval outcomes",
        "fastest_method": "Sandbox IT workflow or redacted historical access-review batch.",
        "success_signal": "Admin says the packet would safely approve/deny or reduce review time.",
        "failure_signal": "Integration/security trust blocks even a sandbox proof.",
        "outreach_script": "Share a redacted access-review batch and policy rules. I will return an approval packet with audit reasons so you can judge if it is safe.",
        "demo_asset": "access review packet and audit log",
    },
    "constellation-buyer-universe": {
        "reachable_customer_access": 3,
        "available_real_sample_data": 2,
        "demo_clarity": 8,
        "willingness_to_pay_signal": 8,
        "integration_complexity": 5,
        "compliance_data_sensitivity": 9,
        "requires_customer_data": True,
        "target_buyer": "boutique and middle-market investment bankers running sell-side buyer universes",
        "required_input": "redacted CIM, banker-built buyer universe, MD include/exclude labels, and prep-time baseline",
        "fastest_method": "Warm banker/advisor willing to share redacted prior-process evidence.",
        "success_signal": "Banker says generated buyers would survive MD review or catch missed buyers.",
        "failure_signal": "No banker can share prior-process evidence or generated buyers miss obvious targets.",
        "outreach_script": "If you can share a redacted prior sell-side pack, I will run a local buyer-universe workflow and return ranked buyers plus MD-review labels.",
        "demo_asset": "review workspace, buyer universe, shadow pilot report",
    },
}


DEFAULT_FACTORS = {
    "reachable_customer_access": 5,
    "available_real_sample_data": 5,
    "demo_clarity": 7,
    "willingness_to_pay_signal": 6,
    "integration_complexity": 5,
    "compliance_data_sensitivity": 5,
    "requires_customer_data": False,
    "target_buyer": "target buyer defined in CUSTOMER.md",
    "required_input": "real or public input matching the product wedge",
    "fastest_method": "manual proof attempt with one target user",
    "success_signal": "target user says the output is useful enough to review, edit, forward, or use",
    "failure_signal": "target user says the output is generic, untrusted, or not worth using",
    "outreach_script": "Can I run a local product on one real or anonymized example from your workflow and ask if the output is useful?",
    "demo_asset": "buyer artifact generated by make demo and make receipt",
}


CATEGORY_LABELS = {
    "proof-now finalists": "A. Proof-now finalists",
    "proof-later contenders": "B. Proof-later contenders",
    "customer-data-required": "C. Customer-data-required",
    "synthetic-ceiling-reached": "D. Synthetic-ceiling-reached",
}


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def merged_factors(repo_name: str) -> dict:
    factors = dict(DEFAULT_FACTORS)
    factors.update(FACTOR_OVERRIDES.get(repo_name, {}))
    return factors


def buyer_pain_from_score(score: int | None) -> int:
    if score is None:
        return 0
    return max(0, min(10, round(score / 10)))


def proof_score(row: dict, factors: dict) -> int:
    buyer_pain = buyer_pain_from_score(row.get("buyer_score"))
    return (
        buyer_pain
        + factors["reachable_customer_access"]
        + factors["available_real_sample_data"]
        + factors["demo_clarity"]
        + factors["willingness_to_pay_signal"]
        - factors["integration_complexity"]
        - factors["compliance_data_sensitivity"]
    )


def row_for_repo(repo: ProductRepo, allocation_by_repo: dict[str, dict]) -> dict:
    allocation = allocation_by_repo.get(repo.repo_name, {})
    factors = merged_factors(repo.repo_name)
    score = proof_score(allocation, factors)
    row = {
        "repo_name": repo.repo_name,
        "product": repo.product,
        "track": repo.track,
        "url": repo.url,
        "buyer_score": allocation.get("buyer_score"),
        "buyer_verdict": allocation.get("buyer_verdict"),
        "allocation_action": allocation.get("action"),
        "proof_priority_score": score,
        "buyer_pain": buyer_pain_from_score(allocation.get("buyer_score")),
        **factors,
    }
    return row


def classify(rows: list[dict], finalists: int) -> list[dict]:
    buyer_compelling = [row for row in rows if row["buyer_verdict"] == "buyer_compelling"]
    ranked = sorted(
        buyer_compelling,
        key=lambda row: (row["proof_priority_score"], row["buyer_score"] or 0, row["product"]),
        reverse=True,
    )
    finalist_names = {
        row["repo_name"]
        for row in ranked[:finalists]
        if row["proof_priority_score"] >= 30 and not row.get("requires_customer_data")
    }

    for row in rows:
        if row["buyer_verdict"] != "buyer_compelling":
            row["category"] = "synthetic-ceiling-reached"
        elif row["repo_name"] in finalist_names:
            row["category"] = "proof-now finalists"
        elif row.get("requires_customer_data"):
            row["category"] = "customer-data-required"
        elif row["proof_priority_score"] >= 24:
            row["category"] = "proof-later contenders"
        else:
            row["category"] = "synthetic-ceiling-reached"
    return sorted(rows, key=lambda row: (row["proof_priority_score"], row["buyer_score"] or 0), reverse=True)


def render_report(rows: list[dict]) -> str:
    finalist_rows = [row for row in rows if row["category"] == "proof-now finalists"]
    lines = [
        "# External Proof Priority Report",
        "",
        "Normal owner development is frozen. This report ranks the product repos by how quickly they can earn real-world proof.",
        "",
        "## Proof-Now Finalists",
        "",
    ]
    for index, row in enumerate(finalist_rows, 1):
        lines.append(
            f"{index}. **{row['product']}** (`{row['repo_name']}`): score {row['proof_priority_score']}. "
            f"Fast proof path: {row['fastest_method']}"
        )
    lines.extend([
        "",
        "## Ranking",
        "",
        "| Rank | Product | Repo | Buyer Score | Proof Score | Category | Target buyer | Required input |",
        "| ---: | --- | --- | ---: | ---: | --- | --- | --- |",
    ])
    for index, row in enumerate(rows, 1):
        buyer_score = "" if row["buyer_score"] is None else str(row["buyer_score"])
        lines.append(
            f"| {index} | {row['product']} | [{row['repo_name']}]({row['url']}) | {buyer_score} | "
            f"{row['proof_priority_score']} | {CATEGORY_LABELS[row['category']]} | {row['target_buyer']} | {row['required_input']} |"
        )
    lines.extend([
        "",
        "## Category Summary",
        "",
    ])
    for category in CATEGORY_LABELS:
        category_rows = [row for row in rows if row["category"] == category]
        names = ", ".join(row["product"] for row in category_rows) or "none"
        lines.append(f"- {CATEGORY_LABELS[category]}: {names}")
    lines.append("")
    return "\n".join(lines)


def render_proof_plan(row: dict) -> str:
    return "\n".join([
        f"# Proof Plan: {row['product']}",
        "",
        "## Target Buyer",
        "",
        row["target_buyer"],
        "",
        "## Required Real-World Input",
        "",
        row["required_input"],
        "",
        "## Fastest Proof Method",
        "",
        row["fastest_method"],
        "",
        "## Success Signal",
        "",
        row["success_signal"],
        "",
        "## Failure Signal",
        "",
        row["failure_signal"],
        "",
        "## Outreach Script",
        "",
        row["outreach_script"],
        "",
        "## Demo Asset",
        "",
        row["demo_asset"],
        "",
        "## Required Packet",
        "",
        "- `EXTERNAL_PROOF_PACKET.md`",
        "- `CUSTOMER_FEEDBACK.md`",
        "- `REAL_DATA_RECEIPT.md` if real or public data is used",
        "- `UPDATED_IC_MEMO.md`",
        "- `FUNDING_RECOMMENDATION.md`",
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--finalists", type=int, default=5, help="Number of proof-now finalist slots.")
    args = parser.parse_args()

    allocation_rows = load_json(ROUND_DIR / "compute_allocation.json", [])
    allocation_by_repo = {row["repo_name"]: row for row in allocation_rows}
    rows = [row_for_repo(repo, allocation_by_repo) for repo in load_product_repos()]
    rows = classify(rows, finalists=args.finalists)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PROOF_PLAN_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(render_report(rows), encoding="utf-8")

    for row in rows:
        if row["category"] != "proof-now finalists":
            continue
        out_dir = PROOF_PLAN_DIR / row["repo_name"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "PROOF_PLAN.md").write_text(render_proof_plan(row), encoding="utf-8")

    print(f"Wrote {OUTPUT_JSON.relative_to(OUTPUT_DIR.parents[1])}")
    print(f"Wrote {OUTPUT_MD.relative_to(OUTPUT_DIR.parents[1])}")
    print("Proof-now finalists:")
    for row in [row for row in rows if row["category"] == "proof-now finalists"]:
        print(f"- {row['product']} ({row['repo_name']}): {row['proof_priority_score']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
