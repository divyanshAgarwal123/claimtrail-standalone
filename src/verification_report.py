"""Validate and replay a captured verification report without running its commands."""
import json
from pathlib import Path
from typing import Optional

from scope_verification import RECEIPT, validate_record, verify
from cli_paths import allowed_path


CASE_FIELDS = {"id", "repository", "scenario", "kind", "expected", "note", "policy",
               "receipt", "observation", "baseline_rerun", "result", "matches_expected"}


def load_report(path: Path, allowed_root: Optional[Path] = None) -> dict:
    path = allowed_path(path, root=allowed_root)
    report = json.loads(path.read_text())
    if report.get("schema") != "claimtrail.verification-report.v1" or not isinstance(report.get("cases"), list) or not report["cases"]:
        raise ValueError("expected a nonempty ClaimTrail verification report")
    seen, cases = set(), []
    for case in report["cases"]:
        if not isinstance(case, dict) or case.keys() - CASE_FIELDS:
            raise ValueError("unsupported fields in verification case")
        cid = case["id"]
        if not isinstance(cid, str) or cid in seen:
            raise ValueError("invalid or duplicate verification case id")
        seen.add(cid)
        result = verify(case["policy"], case.get("receipt"), case["observation"])
        baseline = case.get("baseline_rerun")
        if baseline is not None:
            validate_record(baseline, RECEIPT)
        cases.append({**case, "result": result, "matches_expected": result["status"] == case["expected"]})
    return {**report, "cases": cases, "replayed_cases": len(cases),
            "matching_cases": sum(c["matches_expected"] for c in cases)}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = load_report(args.report)
    print(json.dumps({"cases": report["replayed_cases"], "matching": report["matching_cases"],
                      "note": "Deterministic contract replay, not an independent accuracy benchmark."}))
    raise SystemExit(0 if report["replayed_cases"] == report["matching_cases"] else 1)
