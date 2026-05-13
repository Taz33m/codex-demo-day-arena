"""Helpers for standalone product repo orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
TEAM_REPOS_PATH = ROOT / "published" / "TEAM_REPOS.json"
PRODUCT_REPOS_DIR = ROOT / "product-repos"
REPO_ROUNDS_DIR = ROOT / "repo-rounds"
ROUND_NAME = "round-1"
ROUND_DIR = REPO_ROUNDS_DIR / ROUND_NAME


@dataclass(frozen=True)
class ProductRepo:
    team: str
    product: str
    track: str
    repo_name: str
    url: str

    @property
    def local_path(self) -> Path:
        return PRODUCT_REPOS_DIR / self.repo_name

    @property
    def round_dir(self) -> Path:
        return ROUND_DIR / self.repo_name


def load_product_repos() -> list[ProductRepo]:
    rows = json.loads(TEAM_REPOS_PATH.read_text(encoding="utf-8"))
    return [
        ProductRepo(
            team=row["team"],
            product=row["product"],
            track=row["track"],
            repo_name=row["repo_name"],
            url=row["url"],
        )
        for row in rows
    ]


def select_repos(
    *,
    all_repos: bool = False,
    repo_name: str | None = None,
    team: str | None = None,
    track: str | None = None,
    tier: str | None = None,
) -> list[ProductRepo]:
    repos = load_product_repos()
    if all_repos:
        selected = repos
    elif tier:
        tiers_path = ROUND_DIR / "portfolio_tiers.json"
        if not tiers_path.exists():
            raise SystemExit(f"Missing portfolio tiers: {tiers_path}. Run scripts/tier_product_repos.py first.")
        tier_rows = json.loads(tiers_path.read_text(encoding="utf-8"))
        names = {row["repo_name"] for row in tier_rows if row["tier"] == tier}
        selected = [repo for repo in repos if repo.repo_name in names]
    elif repo_name:
        selected = [repo for repo in repos if repo.repo_name == repo_name]
    elif team:
        selected = [repo for repo in repos if repo.team == team]
    elif track:
        selected = [repo for repo in repos if repo.track == track]
    else:
        raise SystemExit("Select --all, --repo, --team, or --track.")
    if not selected:
        raise SystemExit("No product repos matched selection.")
    return selected


def read_text(path: Path, limit: int | None = None) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    if limit is not None and len(text) > limit:
        return text[:limit].rstrip() + "\n...[truncated]"
    return text


def first_non_heading_lines(text: str, count: int = 5) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(stripped)
        if len(lines) >= count:
            break
    return lines


def ensure_round_dirs(repo: ProductRepo) -> None:
    repo.round_dir.mkdir(parents=True, exist_ok=True)
    (repo.round_dir / "logs").mkdir(parents=True, exist_ok=True)
