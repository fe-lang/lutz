#!/usr/bin/env python3
"""Run the toml-test suite (https://github.com/toml-lang/toml-test) against
the decoder tool (tools/decoder), with the comparison rules of toml-test's runner.

usage: tests/toml_test.py <toml-test checkout> [decoder] [-v] [filter]
"""
import datetime
import itertools
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def datetime_key(kind, text):
    """A comparable form of a date-time, at nanosecond precision like Go's."""
    text = text.replace(" ", "T").replace("t", "T").replace("z", "Z")
    nanos = 0
    if "." in text:
        head, rest = text.split(".", 1)
        digits = "".join(itertools.takewhile(str.isdigit, rest))
        text = head + rest[len(digits):]
        nanos = int((digits + "0" * 9)[:9])
    if kind == "datetime":
        value = datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
        return value.astimezone(datetime.timezone.utc).replace(tzinfo=None), nanos
    if kind == "datetime-local":
        return datetime.datetime.fromisoformat(text), nanos
    if kind == "date-local":
        return datetime.date.fromisoformat(text), nanos
    return datetime.time.fromisoformat(text), nanos


def same(want, have, path="") -> str:
    """'' when equal, else a description of the first difference."""
    if isinstance(want, dict) and set(want) == {"type", "value"} and isinstance(want["type"], str):
        if not isinstance(have, dict) or set(have) != {"type", "value"}:
            return f"{path}: expected a {want['type']} value, got {have!r}"
        kind = want["type"]
        if have["type"] != kind:
            return f"{path}: expected type {kind}, got {have['type']}"
        w, h = want["value"], have["value"]
        if kind == "float":
            if w.lower().lstrip("+-") == "nan" or h.lower().lstrip("+-") == "nan":
                ok = w.lower().lstrip("+-") == h.lower().lstrip("+-")
            else:
                ok = float(w) == float(h)
        elif kind in ("datetime", "datetime-local", "date-local", "time-local"):
            try:
                ok = datetime_key(kind, w) == datetime_key(kind, h)
            except ValueError:
                ok = False
        elif kind == "bool":
            ok = w.lower() == h.lower()
        else:
            ok = w == h
        return "" if ok else f"{path}: expected {w!r}, got {h!r}"
    if isinstance(want, dict):
        if not isinstance(have, dict):
            return f"{path}: expected a table, got {have!r}"
        if set(want) != set(have):
            return f"{path}: keys differ: expected {sorted(want)}, got {sorted(have)}"
        for key in want:
            diff = same(want[key], have[key], f"{path}.{key}")
            if diff:
                return diff
        return ""
    if isinstance(want, list):
        if not isinstance(have, list) or len(want) != len(have):
            return f"{path}: expected an array of {len(want)}, got {have!r}"
        for i, (w, h) in enumerate(zip(want, have)):
            diff = same(w, h, f"{path}[{i}]")
            if diff:
                return diff
        return ""
    return f"{path}: unexpected expectation {want!r}"


def run(decoder, suite, name):
    path = os.path.join(suite, "tests", name)
    data = open(path, "rb").read()
    result = subprocess.run([decoder], input=data, capture_output=True, timeout=20)
    out = result.stdout.decode("utf-8", "replace")
    if name.startswith("invalid/"):
        if result.returncode == 0:
            return name, f"accepted invalid input, output {out.strip()[:200]}"
        return name, ""
    if result.returncode != 0:
        return name, f"rejected valid input: {out.strip()}"
    try:
        have = json.loads(out)
    except ValueError as error:
        return name, f"malformed JSON ({error}): {out[:200]}"
    want = json.load(open(path[: -len(".toml")] + ".json"))
    return name, same(want, have)


def main():
    args = [a for a in sys.argv[1:] if a != "-v"]
    verbose = "-v" in sys.argv
    suite = args[0]
    decoder = args[1] if len(args) > 1 else os.path.join(ROOT, "out", "decoder")
    pattern = args[2] if len(args) > 2 else ""
    names = [
        line.strip()
        for line in open(os.path.join(suite, "tests", "files-toml-1.0.0"))
        if line.strip().endswith(".toml") and pattern in line
    ]
    with ThreadPoolExecutor(16) as pool:
        results = list(pool.map(lambda n: run(decoder, suite, n), names))
    failures = [(n, d) for n, d in results if d]
    for name, diff in failures:
        print(f"FAIL {name}: {diff}" if verbose else f"FAIL {name}")
    valid = sum(n.startswith("valid/") for n in names)
    failed_valid = sum(n.startswith("valid/") for n, _ in failures)
    print(
        f"valid: {valid - failed_valid}/{valid} passed, "
        f"invalid: {len(names) - valid - (len(failures) - failed_valid)}/{len(names) - valid} rejected"
    )
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
