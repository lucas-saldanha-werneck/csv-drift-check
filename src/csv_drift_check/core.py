"""Profile CSV snapshots and compare them. Standard library only."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date

NULLS = {"", "null", "none", "nan", "n/a", "na"}


def infer_type(value: str) -> str:
    v = value.strip()
    if v.lower() in NULLS:
        return "null"
    try:
        int(v)
        return "int"
    except ValueError:
        pass
    try:
        float(v)
        return "float"
    except ValueError:
        pass
    try:
        date.fromisoformat(v)
        return "date"
    except ValueError:
        return "str"


def column_type(types: set[str]) -> str:
    types = types - {"null"}
    if not types:
        return "empty"
    if types == {"int", "float"}:
        return "float"
    if len(types) == 1:
        return next(iter(types))
    return "mixed"


@dataclass
class Profile:
    rows: int
    columns: list[str]
    types: dict[str, str]
    null_rate: dict[str, float]
    key: str | None = None
    keys: set[str] = field(default_factory=set)
    duplicate_keys: int = 0


def profile_csv(path: str, key: str | None = None) -> Profile:
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        columns = list(reader.fieldnames or [])
        if key is not None and key not in columns:
            raise ValueError(f"key column '{key}' not found in {path}")
        seen: dict[str, set[str]] = {c: set() for c in columns}
        nulls = {c: 0 for c in columns}
        keys: set[str] = set()
        dupes = 0
        rows = 0
        for row in reader:
            rows += 1
            for c in columns:
                t = infer_type(row.get(c) or "")
                seen[c].add(t)
                if t == "null":
                    nulls[c] += 1
            if key is not None:
                k = row[key]
                if k in keys:
                    dupes += 1
                keys.add(k)
    return Profile(
        rows=rows,
        columns=columns,
        types={c: column_type(seen[c]) for c in columns},
        null_rate={c: (nulls[c] / rows if rows else 0.0) for c in columns},
        key=key,
        keys=keys,
        duplicate_keys=dupes,
    )


@dataclass
class Finding:
    severity: str  # "error" or "warn"
    message: str


def compare(old: Profile, new: Profile, null_jump: float = 0.10,
            row_change: float = 0.20) -> list[Finding]:
    out: list[Finding] = []
    for c in sorted(set(old.columns) - set(new.columns)):
        out.append(Finding("error", f"column removed: {c}"))
    for c in sorted(set(new.columns) - set(old.columns)):
        out.append(Finding("warn", f"column added: {c}"))
    for c in old.columns:
        if c not in new.types:
            continue
        if old.types[c] != new.types[c]:
            out.append(Finding("error", f"type changed in '{c}': {old.types[c]} -> {new.types[c]}"))
        delta = new.null_rate[c] - old.null_rate[c]
        if delta >= null_jump:
            out.append(Finding(
                "warn",
                f"null rate up in '{c}': {old.null_rate[c]:.0%} -> {new.null_rate[c]:.0%}"))
    if old.rows:
        change = (new.rows - old.rows) / old.rows
        if abs(change) >= row_change:
            out.append(Finding("warn", f"row count changed {change:+.0%}: {old.rows} -> {new.rows}"))
    if new.key:
        if new.duplicate_keys:
            out.append(Finding("error", f"{new.duplicate_keys} duplicate value(s) in key '{new.key}'"))
        if old.key == new.key:
            gone = len(old.keys - new.keys)
            if gone:
                out.append(Finding("warn", f"{gone} key(s) from the old snapshot are missing"))
    return out


def render_markdown(old_path: str, new_path: str, old: Profile, new: Profile,
                    findings: list[Finding]) -> str:
    lines = ["# CSV drift report", "",
             f"- old: `{old_path}` ({old.rows} rows, {len(old.columns)} columns)",
             f"- new: `{new_path}` ({new.rows} rows, {len(new.columns)} columns)", ""]
    if not findings:
        lines.append("No drift found.")
    else:
        lines.append("| Severity | Finding |")
        lines.append("|---|---|")
        for f in findings:
            lines.append(f"| {f.severity} | {f.message} |")
    return "\n".join(lines) + "\n"
