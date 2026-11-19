from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from .calculations import aggregate_groups, build_hs8_monthly
from .discovery import discover, select_sources
from .models import EXPECTED_MONTHS
from .provenance import sha256_text
from .quality import publication_blockers, qa_summary, scope_coverage_issues, validate_sources
from .reporting import PROVISIONAL_WARNING, write_report, write_validation
from .scope import (
    build_candidates,
    create_draft_scope,
    read_scope,
    validate_scope,
    write_candidates,
)

LOGGER = logging.getLogger("epb_power")


def project_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists() and (candidate / "data").is_dir():
            return candidate
    return current


def parser() -> argparse.ArgumentParser:
    root = project_root()
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--data-dir", type=Path, default=root / "data")
    common.add_argument("--config-dir", type=Path, default=root / "config")
    common.add_argument("--output-dir", type=Path)
    result = argparse.ArgumentParser(prog="python -m epb_power", description="EPB power export analysis")
    result.add_argument("--verbose", action="store_true")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("inspect", parents=[common], help="Inspect workbook formats and source selection")
    commands.add_parser("validate", parents=[common], help="Run source and scope QA")
    commands.add_parser("scope-candidates", parents=[common], help="Generate HS8 candidate decision table")
    report = commands.add_parser("report", parents=[common], help="Create Excel, CSV and chart outputs")
    report.add_argument("--allow-incomplete", action="store_true", help="Permit source QA blockers in provisional output")
    report.add_argument("--allow-draft-scope", action="store_true", help="Permit draft scope in provisional output")
    return result


def _load(args: argparse.Namespace) -> tuple[list[Any], dict[str, Any], list[dict[str, str]], list[dict[str, str]]]:
    infos = discover(args.data_dir)
    selected, selection_messages = select_sources(infos)
    candidates = build_candidates(infos)
    args.config_dir.mkdir(parents=True, exist_ok=True)
    write_candidates(candidates, args.config_dir / "hs_scope_candidates.csv")
    scope_path = args.config_dir / "hs_scope.csv"
    created = create_draft_scope(candidates, scope_path)
    if created:
        LOGGER.warning("Created conservative draft scope at %s", scope_path)
    scope = read_scope(scope_path)
    issues = validate_sources(infos, selected, selection_messages)
    issues.extend(scope_coverage_issues(selected, scope))
    for item in validate_scope(scope):
        item.setdefault("source_file", "")
        issues.append(item)
    return infos, selected, scope, issues


def run_inspect(args: argparse.Namespace) -> int:
    infos = discover(args.data_dir)
    selected, messages = select_sources(infos)
    for info in infos:
        counts = ", ".join(f"HS{level}={info.counts.get(level, 0)}" for level in (2, 4, 6, 8))
        total = "NA" if info.reported_total_cents is None else f"{info.reported_total_cents / 100:,.2f}"
        print(
            f"{info.filename}: period={info.period or 'UNKNOWN'} format={info.report_format} "
            f"header={'OK' if info.header_valid else 'INVALID'} {counts} chapters={len(info.chapters)} "
            f"total_usd={total} selected={'Y' if info.selected else 'N'} reason={info.selection_reason}"
        )
    print(f"\nSelected {len(selected)}/{len(EXPECTED_MONTHS)} authoritative month sources")
    for message in messages:
        print(f"- {message}")
    return 0 if len(selected) == len(EXPECTED_MONTHS) else 2


def run_scope(args: argparse.Namespace) -> int:
    infos = discover(args.data_dir)
    candidates = build_candidates(infos)
    args.config_dir.mkdir(parents=True, exist_ok=True)
    candidate_path = args.config_dir / "hs_scope_candidates.csv"
    write_candidates(candidates, candidate_path)
    created = create_draft_scope(candidates, args.config_dir / "hs_scope.csv")
    print(f"Wrote {len(candidates)} candidates to {candidate_path}")
    print("Created conservative draft config/hs_scope.csv" if created else "Preserved existing config/hs_scope.csv")
    return 0


def run_validate(args: argparse.Namespace) -> int:
    infos, selected, scope, issues = _load(args)
    detail, calculation_issues = build_hs8_monthly(selected, scope)
    issues.extend(calculation_issues)
    summary = qa_summary(issues)
    summary.update(
        {
            "source_files": len(infos),
            "selected_months": len(selected),
            "expected_months": len(EXPECTED_MONTHS),
            "included_hs8": sum(row.get("include", "").upper() == "Y" for row in scope),
            "detail_records": len(detail),
        }
    )
    output = args.output_dir or project_root() / "outputs" / "diagnostics"
    write_validation(output, infos, issues, summary)
    print(json.dumps(summary, indent=2))
    print(f"Diagnostics written to {output}")
    return 2 if summary["status"] == "FAIL" else 0


def run_report(args: argparse.Namespace) -> int:
    infos, selected, scope, issues = _load(args)
    detail, calculation_issues = build_hs8_monthly(selected, scope)
    issues.extend(calculation_issues)
    summary = qa_summary(issues)
    diagnostics = project_root() / "outputs" / "diagnostics"
    write_validation(diagnostics, infos, issues, summary)
    critical_codes = {i["issue_code"] for i in issues if i["severity"] == "critical"}
    blockers = publication_blockers(
        issues,
        allow_incomplete=args.allow_incomplete,
        allow_draft_scope=args.allow_draft_scope,
    )
    draft_block = "scope_not_approved" in critical_codes
    source_or_data_blocks = critical_codes - {"scope_not_approved"}
    if blockers:
        print("Strict report stopped by QA gates. Review outputs/diagnostics/validation_summary.md.", file=sys.stderr)
        if draft_block and not args.allow_draft_scope:
            print("Included HS8 scope is draft; approve it or rerun with --allow-draft-scope.", file=sys.stderr)
        if source_or_data_blocks and not args.allow_incomplete:
            print(f"Critical source/data issue codes: {', '.join(sorted(source_or_data_blocks))}", file=sys.stderr)
        return 2
    monthly = aggregate_groups(detail, scope)
    provisional = bool(critical_codes or args.allow_draft_scope or args.allow_incomplete)
    output = args.output_dir or project_root() / "outputs" / ("provisional" if provisional else "final")
    report_path = write_report(
        output,
        project_root() / "outputs" / "charts",
        infos,
        issues,
        scope,
        detail,
        monthly,
        provisional,
        sha256_text(args.config_dir / "hs_scope.csv"),
    )
    print(PROVISIONAL_WARNING if provisional else "VALIDATED FINAL REPORT")
    print(f"Created {report_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    handlers = {
        "inspect": run_inspect,
        "validate": run_validate,
        "scope-candidates": run_scope,
        "report": run_report,
    }
    return handlers[args.command](args)

