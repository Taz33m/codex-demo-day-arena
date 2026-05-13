#!/usr/bin/env python3
"""Launch Codex owner agents from inside standalone product repos."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import tempfile
from pathlib import Path

from product_repos import ROOT, ROUND_DIR, REPO_ROUNDS_DIR, ProductRepo, read_text, select_repos


DEFAULT_MODEL = "gpt-5.5"
DEFAULT_REASONING = "xhigh"
DEFAULT_PROMPT = ROOT / "prompts" / "repo-owner-round1.md"
DEFAULT_BRANCH = "codex/round-1-owner"
STATUS_PATH = ROUND_DIR / "product_repo_status.json"


def probe_model(model: str, reasoning: str, timeout: int) -> None:
    with tempfile.NamedTemporaryFile(prefix="codex-repo-owner-probe-", suffix=".txt", delete=False) as output:
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
            "Model probe timed out. Refusing to launch repo owners.\n"
            f"model={model} reasoning={reasoning} timeout={timeout}s\n"
            f"stdout_tail={partial[-2000:]}"
        ) from None
    output_text = read_text(Path(output_path)).strip()
    if proc.returncode != 0 or "OK" not in output_text:
        raise SystemExit(
            "Model probe failed. Refusing to launch repo owners.\n"
            f"model={model} reasoning={reasoning} exit={proc.returncode}\n"
            f"last_message={output_text!r}\n"
            f"stdout_tail={proc.stdout[-2000:]}"
        )


def dirty_paths(repo: ProductRepo) -> list[str]:
    proc = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo.local_path,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(f"{repo.repo_name}: git status failed\n{proc.stdout[-2000:]}")
    paths: list[str] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        paths.append(line[3:].strip())
    return paths


def generated_dirty_only(paths: list[str]) -> bool:
    if not paths:
        return True
    allowed_exact = {"evidence/demo_receipt.json", "evidence/eval_results.json", "app/eval_results.json"}
    allowed_prefixes = ("app/out/", "app/output/", "app/outputs/")
    return all(path in allowed_exact or path.startswith(allowed_prefixes) for path in paths)


def ensure_branch(repo: ProductRepo, branch: str) -> None:
    dirty = dirty_paths(repo)
    if dirty and not generated_dirty_only(dirty):
        raise SystemExit(
            f"{repo.repo_name}: local repo has non-generated uncommitted changes; refusing to switch branch.\n"
            + "\n".join(dirty)
        )
    if dirty:
        print(f"{repo.repo_name}: carrying generated validation changes onto {branch}: {', '.join(dirty)}")
    subprocess.run(["git", "switch", "-C", branch], cwd=repo.local_path, check=True)


def allocation_repos(action: str) -> list[ProductRepo]:
    allocation_path = ROUND_DIR / "compute_allocation.json"
    if not allocation_path.exists():
        raise SystemExit(f"Missing compute allocation: {allocation_path}")
    rows = json.loads(allocation_path.read_text(encoding="utf-8"))
    names = {row["repo_name"] for row in rows if row.get("action") == action}
    return [repo for repo in select_repos(all_repos=True) if repo.repo_name in names]


def ready_state_repos(ready: bool) -> list[ProductRepo]:
    if not STATUS_PATH.exists():
        raise SystemExit(f"Missing product status: {STATUS_PATH}. Run scripts/validate_product_repos.py first.")
    rows = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    names = {row["repo_name"] for row in rows if bool(row.get("ready")) is ready}
    return [repo for repo in select_repos(all_repos=True) if repo.repo_name in names]


def shell_command(repo: ProductRepo, model: str, reasoning: str, prompt_path: Path, brief_path: Path) -> str:
    prompt_rel = os.path.relpath(prompt_path, repo.local_path)
    brief_rel = os.path.relpath(brief_path, repo.local_path)
    return (
        f"cd {repo.local_path.relative_to(ROOT)} && "
        f"codex exec --full-auto --ephemeral -m {model} "
        f"-c model_reasoning_effort='\"{reasoning}\"' \"$(cat {prompt_rel} {brief_rel})\""
    )


def launch_one(
    repo: ProductRepo,
    prompt_text: str,
    model: str,
    reasoning: str,
    round_dir: Path,
    prompt_path: Path,
) -> tuple[subprocess.Popen, Path]:
    repo_round_dir = round_dir / repo.repo_name
    repo_round_dir.mkdir(parents=True, exist_ok=True)
    (repo_round_dir / "logs").mkdir(parents=True, exist_ok=True)
    if not repo.local_path.exists():
        raise SystemExit(f"{repo.repo_name}: missing local repo. Run scripts/sync_product_repos.py first.")
    brief_path = repo_round_dir / "OWNER_BRIEF.md"
    brief = read_text(brief_path)
    if not brief:
        raise SystemExit(f"{repo.repo_name}: missing owner brief. Run scripts/prepare_repo_round.py first.")
    full_prompt = f"{prompt_text}\n\n# Repo-Specific Owner Brief\n\n{brief}"
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = repo_round_dir / "logs" / f"repo-owner-{stamp}.log"
    with log_file.open("w", encoding="utf-8") as log:
        log.write(f"# Repo Owner Launch: {repo.repo_name}\n")
        log.write(f"# Repo: {repo.url}\n")
        log.write(f"# Model: {model}\n")
        log.write(f"# Reasoning: {reasoning}\n")
        log.write(f"# Cwd: {repo.local_path}\n")
        log.write(f"# Command: {shell_command(repo, model, reasoning, prompt_path, brief_path)}\n\n")
        log.flush()
        proc = subprocess.Popen(
            [
                "codex",
                "exec",
                "--full-auto",
                "--ephemeral",
                "-m",
                model,
                "-c",
                f'model_reasoning_effort="{reasoning}"',
                full_prompt,
            ],
            cwd=repo.local_path,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            text=True,
        )
    print(f"{repo.repo_name}: started pid={proc.pid} log={log_file.relative_to(ROOT)}")
    return proc, log_file


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
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--reasoning", default=DEFAULT_REASONING)
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    parser.add_argument("--round-name", default="round-1")
    parser.add_argument("--prompt", default=str(DEFAULT_PROMPT))
    parser.add_argument("--no-branch", action="store_true")
    parser.add_argument("--probe-timeout", type=int, default=90)
    parser.add_argument("--skip-model-check", action="store_true")
    parser.add_argument("--wait", action="store_true")
    args = parser.parse_args()

    if args.ready and args.not_ready:
        raise SystemExit("Use only one of --ready or --not-ready.")
    if args.allocation_action:
        repos = allocation_repos(args.allocation_action)
        if not repos:
            raise SystemExit(f"No repos matched allocation action: {args.allocation_action}")
    elif args.ready:
        repos = ready_state_repos(True)
    elif args.not_ready:
        repos = ready_state_repos(False)
    else:
        repos = select_repos(all_repos=args.all, repo_name=args.repo, team=args.team, track=args.track, tier=args.tier)
    prompt_path = Path(args.prompt)
    if not prompt_path.is_absolute():
        prompt_path = ROOT / prompt_path
    round_dir = REPO_ROUNDS_DIR / args.round_name
    prompt_text = read_text(prompt_path)
    if not prompt_text:
        raise SystemExit(f"Missing prompt: {prompt_path}")

    if not args.execute:
        args.dry_run = True

    if not args.skip_model_check:
        probe_model(args.model, args.reasoning, args.probe_timeout)

    if args.dry_run:
        for repo in repos:
            brief_path = round_dir / repo.repo_name / "OWNER_BRIEF.md"
            print(shell_command(repo, args.model, args.reasoning, prompt_path, brief_path))
        return 0

    if not args.no_branch:
        for repo in repos:
            ensure_branch(repo, args.branch)

    launched = [launch_one(repo, prompt_text, args.model, args.reasoning, round_dir, prompt_path) for repo in repos]
    if args.wait:
        exit_code = 0
        for repo, (proc, log_file) in zip(repos, launched):
            code = proc.wait()
            print(f"{repo.repo_name}: exited code={code} log={log_file.relative_to(ROOT)}")
            if code != 0:
                exit_code = code
        return exit_code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
