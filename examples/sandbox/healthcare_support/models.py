from __future__ import annotations

import os as _os
import sys as _sys
from pathlib import Path as _Path


def _load_repo_env() -> None:
    for _directory in _Path(__file__).resolve().parents:
        _src_path = _directory / "src"
        if _src_path.exists():
            _root = str(_directory)
            if _root not in _sys.path:
                _sys.path.insert(0, _root)
            _src = str(_src_path)
            if _src not in _sys.path:
                _sys.path.insert(0, _src)

        _venv_path = _directory / ".venv"
        if _venv_path.exists():
            _site_packages = next(_venv_path.glob("lib/python*/site-packages"), None)
            if _site_packages is not None:
                _site = str(_site_packages)
                if _site not in _sys.path:
                    _sys.path.insert(1 if _src_path.exists() else 0, _site)

        _env_path = _directory / ".env"
        if not _env_path.exists():
            continue

        for _line in _env_path.read_text().splitlines():
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _key, _value = _line.split("=", 1)
            _os.environ.setdefault(_key.strip(), _value.strip().strip("\"'"))
        return


_load_repo_env()


from typing import Any, Literal

from pydantic import BaseModel, Field

IntentName = Literal[
    "eligibility_verification",
    "prior_auth_confusion",
    "referral_status_question",
    "billing_coverage_clarification",
    "general_intake",
]


class ScenarioExpectation(BaseModel):
    intent: IntentName
    required_entities: dict[str, str] = Field(default_factory=dict)
    required_tool_calls: list[str] = Field(default_factory=list)
    required_resolution_elements: list[str] = Field(default_factory=list)
    expected_payer: str | None = None


class ScenarioCase(BaseModel):
    scenario_id: str
    description: str
    transcript: str
    patient_metadata: dict[str, Any] = Field(default_factory=dict)
    followup_qa: dict[str, str] = Field(default_factory=dict)
    expected: ScenarioExpectation
    gold: dict[str, Any] = Field(default_factory=dict)


class KnowledgeSnippet(BaseModel):
    document_id: str
    title: str
    chunk_id: str
    score: float
    snippet: str
    matched_terms: list[str] = Field(default_factory=list)


class BenefitReview(BaseModel):
    patient_name: str
    patient_id: str
    payer: str
    member_id: str
    eligibility_status: str
    plan_summary: str
    referral_status: str
    prior_auth_recommended: bool
    recommended_queue: str
    summary: str


class SandboxPolicyPacket(BaseModel):
    matched_policy_files: list[str] = Field(default_factory=list)
    generated_files: list[str] = Field(default_factory=list)
    shell_commands: list[str] = Field(default_factory=list)
    policy_summary: str
    human_review_recommended: bool


class CaseResolution(BaseModel):
    scenario_id: str
    intent: IntentName
    patient_name: str
    benefits_summary: str
    policy_summary: str
    next_step: str
    route_to_human: bool
    handoff_id: str | None = None
    generated_files: list[str] = Field(default_factory=list)
    internal_summary: str
    patient_facing_response: str


class MemoryRecap(BaseModel):
    remembered_patient: str | None = None
    remembered_intent: IntentName | None = None
    remembered_next_step: str
    remembered_handoff: str | None = None
    remembered_files: list[str] = Field(default_factory=list)
