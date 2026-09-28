"""Paperclip run context and run-scoped Nerve profile helpers."""
from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Mapping

from ..profiles import PROFILE_NAMES, normalize_profile_name


@dataclass(frozen=True)
class PaperclipRunContext:
    company_id: str
    task_id: str
    run_id: str
    agent_id: str
    api_url: str = ""
    role: str = ""


@dataclass(frozen=True)
class RuntimeProfileOverride:
    profile: str
    source: str


PAPERCLIP_ROLE_PROFILES = {
    "director": "operator",
    "builder": "lean",
    "reviewer": "fat_cat",
    "maintenance": "marie_kondo",
}

_CONTEXT_KEYS = (
    "PAPERCLIP_COMPANY_ID",
    "PAPERCLIP_TASK_ID",
    "PAPERCLIP_RUN_ID",
    "PAPERCLIP_AGENT_ID",
)


def _clean(value: object) -> str:
    return str(value or "").strip()


def detect_paperclip_context(
    env: Mapping[str, str] | None = None,
) -> PaperclipRunContext | None:
    """Return the current Paperclip run identity without retaining credentials.

    Paperclip's Hermes adapter injects PAPERCLIP_TASK_ID for issue-triggered
    runs. PAPERCLIP_API_KEY is deliberately excluded from this object.
    """
    source = os.environ if env is None else env
    present = {key: _clean(source.get(key)) for key in _CONTEXT_KEYS}
    if not any(present.values()):
        return None
    missing = [key for key, value in present.items() if not value]
    if missing:
        raise ValueError(
            "Incomplete Paperclip run context; missing " + ", ".join(sorted(missing))
        )
    return PaperclipRunContext(
        company_id=present["PAPERCLIP_COMPANY_ID"],
        task_id=present["PAPERCLIP_TASK_ID"],
        run_id=present["PAPERCLIP_RUN_ID"],
        agent_id=present["PAPERCLIP_AGENT_ID"],
        api_url=_clean(source.get("PAPERCLIP_API_URL")),
        role=_clean(source.get("PAPERCLIP_AGENT_ROLE")).lower(),
    )


def runtime_profile_override(
    env: Mapping[str, str] | None = None,
) -> RuntimeProfileOverride | None:
    """Resolve a per-run profile without writing the persistent profile sidecar."""
    source = os.environ if env is None else env
    explicit = normalize_profile_name(source.get("HERMES_NERVE_RUNTIME_PROFILE"))
    if explicit:
        if explicit not in PROFILE_NAMES:
            raise ValueError(f"Unknown runtime Nerve profile: {explicit}")
        return RuntimeProfileOverride(explicit, "environment")

    role = _clean(source.get("PAPERCLIP_AGENT_ROLE")).lower()
    mapped = PAPERCLIP_ROLE_PROFILES.get(role)
    if mapped:
        return RuntimeProfileOverride(mapped, "paperclip-role")
    return None
