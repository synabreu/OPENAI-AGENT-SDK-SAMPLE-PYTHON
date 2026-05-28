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

from typing import Literal

from pydantic import BaseModel, Field


class FinancialMetric(BaseModel):
    source_file: str = Field(
        description="Workspace-relative source path under data/, such as data/10-k-mdna-overview.txt."
    )
    filing_section: Literal[
        "Part II, Item 7. Management's Discussion and Analysis of Financial Condition and Results of Operations",
        "Part II, Item 8. Financial Statements and Supplementary Data",
    ] = Field(description="Normalized 10-K filing section for the source document.")
    metric_name: str = Field(
        description="Metric label exactly as written in the source document or table."
    )
    fiscal_period: Literal["FY2025", "FY2024", "2025-12-31", "2024-12-31"] = Field(
        description="Annual period label for statement rows, or balance-sheet date for point-in-time rows."
    )
    value: float = Field(description="Numeric value from the source row.")
    unit: Literal["USD millions", "percent"] = Field(
        description="Unit for `value`; use USD millions for dollar amounts and percent for margins."
    )
    segment: str | None = Field(
        default=None,
        description="Reportable segment or geography when the row is segment-specific, otherwise null.",
    )


class FinancialMetricBatch(BaseModel):
    metrics: list[FinancialMetric] = Field(
        description="One row per metric-period pair extracted from each source document."
    )
