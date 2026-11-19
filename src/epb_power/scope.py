from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from .models import WorkbookInfo

FAMILIES = {
    "Transformers": ("850421", "850422", "850423", "850431", "850432", "850433", "850434"),
    "Switchgear & protection": ("8535", "8536"),
    "Distribution & control panels": ("8537",),
    "Power cables & conductors": ("8544",),
    "Solar PV cells & modules": ("854143",),
    "Industrial & storage batteries": ("8507",),
    "Grid-relevant inverters & converters": ("850440",),
    "Electricity meters": ("902830",),
}

CANDIDATE_COLUMNS = [
    "hs8",
    "description",
    "proposed_group",
    "observed_files_or_months",
    "suggested_include",
    "reason",
    "needs_review",
]
SCOPE_COLUMNS = ["hs8", "product_group", "include", "review_status", "decision_note", "description"]


def proposed_group(code: str) -> str | None:
    for group, prefixes in FAMILIES.items():
        if code.startswith(prefixes):
            return group
    return None


def conservative_decision(code: str, description: str, group: str) -> tuple[str, str, str]:
    text = description.lower()
    if group == "Transformers":
        return "Y", "Exact transformer HS6 family named in specification", "N"
    if group == "Solar PV cells & modules":
        return "Y", "Exact photovoltaic cells/modules HS6 family", "N"
    if group == "Electricity meters":
        return "Y", "Exact electricity-meter HS6 family", "N"
    if group == "Distribution & control panels":
        return "Y", "Board/panel HS4 for electric control or distribution", "N"
    if group == "Switchgear & protection":
        excluded = ("lamp-holder", "lamp holder", "plugs and sockets", "connector", "junction box")
        if any(word in text for word in excluded):
            return "N", "Accessory/general connection item excluded conservatively", "Y"
        if any(
            word in text
            for word in (
                "other switches",
                "relays for a voltage =<60",
                "apparatus for switching... electrical circuits, nes",
            )
        ):
            return "N", "Generic/low-voltage description does not establish power-sector use", "Y"
        power_terms = (
            "fuse",
            "circuit breaker",
            "relay",
            "switch",
            "lightning arrester",
            "surge suppressor",
            "protecting electrical circuits",
        )
        if any(word in text for word in power_terms):
            return "Y", "Description supports switching/protection function", "Y"
        return "N", "Description does not establish grid/power function", "Y"
    if group == "Power cables & conductors":
        excluded = ("optical fibre", "co-axial", "coaxial", "ignition wiring", "telecommunication")
        if any(word in text for word in excluded):
            return "N", "Telecom/optical/vehicle-specific cabling excluded", "N"
        if "exceeding 1000v" in text or "exceeding 1,000 v" in text:
            return "Y", "High-voltage electric conductor supports power-grid classification", "N"
        if any(word in text for word in ("electric conductor", "wire", "cable", "winding wire")):
            return "N", "General/low-voltage conductor end-use is not demonstrably power-sector", "Y"
        return "N", "Description is not clearly power cable/conductor", "Y"
    if group == "Industrial & storage batteries":
        if code.startswith("850710") or "starting piston engines" in text:
            return "N", "Automotive starter battery excluded", "N"
        return "N", "Battery end-use is not proven stationary/industrial", "Y"
    if group == "Grid-relevant inverters & converters":
        if "solar" in text and "inverter" in text:
            return "Y", "Description explicitly identifies solar inverter", "N"
        return "N", "Generic static converter cannot be labelled grid/solar", "Y"
    return "N", "Unclassified candidate", "Y"


def build_candidates(infos: list[WorkbookInfo]) -> list[dict[str, str]]:
    observed: dict[str, set[str]] = defaultdict(set)
    descriptions: dict[str, str] = {}
    for info in infos:
        if not info.header_valid:
            continue
        for code, row in info.hs8.items():
            group = proposed_group(code)
            if group:
                if code not in descriptions or len(row.description.strip()) > len(descriptions[code].strip()):
                    descriptions[code] = row.description
                observed[code].add(f"{info.period}:{info.filename}")
    for code, description in list(descriptions.items()):
        if description.strip():
            continue
        parent_descriptions: list[tuple[int, str]] = []
        for info in infos:
            by_code = {row.code: row.description for row in info.rows}
            for parent in (code[:6], code[:4]):
                if by_code.get(parent, "").strip():
                    parent_descriptions.append((len(parent), by_code[parent].strip()))
        if parent_descriptions:
            level, parent_description = max(parent_descriptions, key=lambda item: (item[0], len(item[1])))
            descriptions[code] = f"[HS{level} parent; source HS8 description blank] {parent_description}"
    records: list[dict[str, str]] = []
    for code in sorted(observed):
        group = proposed_group(code) or ""
        include, reason, needs_review = conservative_decision(code, descriptions[code], group)
        records.append(
            {
                "hs8": code,
                "description": descriptions[code],
                "proposed_group": group,
                "observed_files_or_months": " | ".join(sorted(observed[code])),
                "suggested_include": include,
                "reason": reason,
                "needs_review": needs_review,
            }
        )
    return records


def write_candidates(records: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANDIDATE_COLUMNS)
        writer.writeheader()
        writer.writerows(records)


def create_draft_scope(records: list[dict[str, str]], path: Path) -> bool:
    if path.exists():
        return False
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=SCOPE_COLUMNS)
        writer.writeheader()
        for item in records:
            writer.writerow(
                {
                    "hs8": item["hs8"],
                    "product_group": item["proposed_group"],
                    "include": item["suggested_include"],
                    "review_status": "draft",
                    "decision_note": item["reason"],
                    "description": item["description"],
                }
            )
    return True


def read_scope(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def validate_scope(records: list[dict[str, str]]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    seen: dict[str, str] = {}
    for index, item in enumerate(records, 2):
        code = item.get("hs8", "")
        include = item.get("include", "").upper()
        status = item.get("review_status", "").lower()
        if len(code) != 8 or not code.isdigit():
            issues.append(_issue("critical", "scope_invalid_code", "scope", f"row {index}: {code!r}"))
        if include not in {"Y", "N"}:
            issues.append(_issue("critical", "scope_invalid_include", "scope", f"{code}: {include!r}"))
        if status not in {"approved", "draft"}:
            issues.append(_issue("critical", "scope_invalid_status", "scope", f"{code}: {status!r}"))
        if code in seen:
            issues.append(_issue("critical", "scope_duplicate_code", "scope", f"{code} duplicated"))
        seen[code] = item.get("product_group", "")
        if include == "Y" and not item.get("product_group", "").strip():
            issues.append(_issue("critical", "scope_missing_group", "scope", f"{code} included without group"))
    included = [item for item in records if item.get("include", "").upper() == "Y"]
    if not included:
        issues.append(_issue("critical", "scope_empty", "scope", "No included HS8 codes"))
    if any(item.get("review_status", "").lower() != "approved" for item in included):
        issues.append(_issue("critical", "scope_not_approved", "scope", "Included scope contains draft decisions"))
    return issues


def _issue(severity: str, code: str, period: str, message: str) -> dict[str, str]:
    return {"severity": severity, "issue_code": code, "period": period, "message": message}

