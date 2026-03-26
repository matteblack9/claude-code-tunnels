"""Helpers for loading local skill playbooks into orchestrator prompts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import yaml

from orchestrator import BASE


@dataclass(frozen=True, slots=True)
class SkillDocument:
    """Parsed skill metadata plus markdown body."""

    name: str
    description: str
    path: Path
    body: str


SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "setup-orchestrator": (
        "setup orchestrator",
        "reconfigure orchestrator",
        "bootstrap orchestrator",
        "install orchestrator",
        "project orchestrator",
        "environment setup",
        "orchestrator",
        "setup tui",
        "환경 구성",
        "환경 설정",
        "오케스트레이터",
        "설치",
        "재설정",
        "초기화",
    ),
    "connect-slack": (
        "connect slack",
        "slack channel",
        "slack bot",
        "socket mode",
        "슬랙",
        "슬랙 연결",
    ),
    "connect-telegram": (
        "connect telegram",
        "telegram bot",
        "botfather",
        "텔레그램",
        "텔레그램 연결",
    ),
    "setup-remote-project": (
        "remote project",
        "deploy listener",
        "remote listener",
        "ssh listener",
        "kubectl listener",
        "원격 프로젝트",
        "원격 리스너",
        "리스너 배포",
    ),
    "setup-remote-workspace": (
        "remote workspace",
        "workspace listener",
        "single workspace remote",
        "원격 워크스페이스",
        "워크스페이스 리스너",
    ),
}

GENERIC_SKILL_HINTS = (
    "skill",
    "skills",
    "skill.md",
    "setup",
    "configure",
    "configuration",
    "connect",
    "channel",
    "remote",
    "workspace",
    "orchestrator",
    "runtime",
    "slack",
    "telegram",
    "listener",
    "deploy",
    "환경",
    "설정",
    "구성",
    "연결",
    "원격",
    "워크스페이스",
    "런타임",
    "오케스트레이터",
    "슬랙",
    "텔레그램",
    "리스너",
)


def _split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text.strip()

    match = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.DOTALL)
    if not match:
        return {}, text.strip()

    raw_frontmatter, body = match.groups()
    parsed = yaml.safe_load(raw_frontmatter) or {}
    return parsed if isinstance(parsed, dict) else {}, body.strip()


def _tokenize(text: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9가-힣]+", text.casefold()) if len(token) >= 2}


def discover_skill_documents(base_dir: Path | None = None) -> list[SkillDocument]:
    """Load skill docs from <base>/skills/*/SKILL.md."""
    skill_root = (base_dir or BASE) / "skills"
    if not skill_root.is_dir():
        return []

    documents: list[SkillDocument] = []
    for path in sorted(skill_root.glob("*/SKILL.md")):
        text = path.read_text(encoding="utf-8")
        metadata, body = _split_frontmatter(text)
        name = str(metadata.get("name") or path.parent.name).strip() or path.parent.name
        description = str(metadata.get("description") or "").strip()
        documents.append(
            SkillDocument(
                name=name,
                description=description,
                path=path.resolve(),
                body=body,
            )
        )
    return documents


def _score_skill_match(task_text: str, document: SkillDocument) -> int:
    text = task_text.casefold()
    tokens = _tokenize(task_text)
    keywords = _tokenize(f"{document.name} {document.description} {document.path.parent.name}")
    aliases = tuple(alias.casefold() for alias in SKILL_ALIASES.get(document.name, ()))

    score = 0
    if document.name.casefold() in text:
        score += 10
    if document.path.parent.name.replace("-", " ").casefold() in text:
        score += 6
    score += sum(5 for alias in aliases if alias in text)
    score += len(tokens & keywords)

    if document.name.startswith("setup-") and any(
        hint in text for hint in ("setup", "configure", "install", "bootstrap", "환경", "설정", "설치", "구성")
    ):
        score += 1

    return score


def select_relevant_skills(
    task_text: str,
    base_dir: Path | None = None,
    limit: int = 3,
) -> list[SkillDocument]:
    """Return the most relevant skills for the current request."""
    documents = discover_skill_documents(base_dir)
    if not documents:
        return []

    lowered = task_text.casefold()
    if any(hint in lowered for hint in ("skills/", "skill.md", "skil.md", "skill ")) and "connect" not in lowered:
        return documents[:limit]

    scored = [
        (score, document)
        for document in documents
        if (score := _score_skill_match(task_text, document)) > 0
    ]
    scored.sort(key=lambda item: (-item[0], item[1].name))

    if scored:
        return [document for _, document in scored[:limit]]

    if any(hint in lowered for hint in GENERIC_SKILL_HINTS):
        for document in documents:
            if document.name == "setup-orchestrator":
                return [document]
    return []


def build_skills_prompt(
    task_text: str,
    base_dir: Path | None = None,
    *,
    include_full_text: bool = True,
) -> str:
    """Render a prompt block that preloads repo-local skills."""
    documents = discover_skill_documents(base_dir)
    if not documents:
        return ""

    skill_root = ((base_dir or BASE) / "skills").resolve()
    lines = [
        "## Local Skill Playbooks",
        f"- The Project Orchestrator ships environment/setup playbooks under `{skill_root}`.",
        "- Before planning or executing, compare the request against the catalog below.",
        "- If a skill matches, follow that `SKILL.md` as the primary operating procedure instead of inventing a parallel workflow.",
        "- Use the runtime-specific sections inside each `SKILL.md` for Claude, Cursor, Codex, and OpenCode behavior.",
        "Available skills:",
    ]
    lines.extend(
        f"- `{document.name}` — {document.description or 'No description provided.'} ({document.path})"
        for document in documents
    )

    if not include_full_text:
        return "\n".join(lines)

    relevant = select_relevant_skills(task_text, base_dir)
    if not relevant:
        lines.append(
            "No specific skill was auto-matched. If the task becomes environment, channel, or remote setup work, read the matching skill before continuing."
        )
        return "\n".join(lines)

    lines.append("Relevant skills preloaded for this request:")
    for document in relevant:
        lines.append(
            f'<skill name="{document.name}" path="{document.path}">\n{document.body}\n</skill>'
        )
    return "\n".join(lines)
