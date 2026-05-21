from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from benchmarks.vsm.data.schema import VALID_SPLITS, default_dataset_path, load_vsm_cases, summarize_cases


RAW_SPEC_FILES = (
    "cbt_probe.json",
    "mbi_probe.json",
    "ba_probe.json",
    "safety_probe.json",
    "yalom_probe.json",
    "cbt_sessions.json",
    "mbi_sessions.json",
    "ba_sessions.json",
    "safety_sessions.json",
    "yalom_sessions.json",
    "cbt_stress.json",
    "mbi_stress.json",
    "ba_stress.json",
    "safety_stress.json",
    "yalom_stress.json",
)


def default_raw_specs_dir() -> Path:
    return Path(__file__).with_name("raw_specs")


def build_cases(raw_specs_dir: str | Path | None = None, *, split: str | None = None) -> list[dict[str, Any]]:
    specs_dir = Path(raw_specs_dir) if raw_specs_dir else default_raw_specs_dir()
    cases: list[dict[str, Any]] = []

    for path in _raw_spec_paths(specs_dir):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"VSM raw spec file must contain an array: {path}")
        cases.extend(item for item in payload if split is None or item.get("split") == split)

    return cases


def _raw_spec_paths(specs_dir: Path) -> list[Path]:
    nested_paths = sorted(path for path in specs_dir.glob("*/*.json") if path.is_file())
    if nested_paths:
        return nested_paths

    legacy_paths = [specs_dir / filename for filename in RAW_SPEC_FILES if (specs_dir / filename).exists()]
    if legacy_paths:
        return legacy_paths

    raise FileNotFoundError(f"No VSM raw spec JSON files found under: {specs_dir}")


def write_dataset(cases: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for item in cases:
            handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the canonical VSM inference dataset from raw specs.")
    parser.add_argument("--raw-specs-dir", type=Path, default=default_raw_specs_dir())
    parser.add_argument("--out", type=Path, default=default_dataset_path())
    parser.add_argument("--split", choices=sorted(VALID_SPLITS))
    parser.add_argument("--write-standard-outputs", action="store_true")
    args = parser.parse_args()

    if args.write_standard_outputs:
        output_dir = args.out.parent
        outputs = {
            "probe": output_dir / "vsm_probe.jsonl",
            "session_core": output_dir / "vsm_session_core.jsonl",
            "stress": output_dir / "vsm_stress.jsonl",
            None: output_dir / "vsm_all.jsonl",
        }
        for split, output_path in outputs.items():
            write_dataset(build_cases(args.raw_specs_dir, split=split), output_path)
            cases = load_vsm_cases(output_path)
            print(f"\n# {output_path}")
            print(json.dumps(summarize_cases(cases), ensure_ascii=False, indent=2))
        write_dataset(build_cases(args.raw_specs_dir, split="session_core"), output_dir / "vsm_cases.jsonl")
        return

    write_dataset(build_cases(args.raw_specs_dir, split=args.split), args.out)
    cases = load_vsm_cases(args.out)
    print(json.dumps(summarize_cases(cases), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
