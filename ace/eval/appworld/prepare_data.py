import argparse
import json
import os
from typing import Any, Dict, List


def parse_args():
    parser = argparse.ArgumentParser(description="Prepare AppWorld metadata JSONL")
    parser.add_argument("--input_json", type=str, required=True)
    parser.add_argument("--output_jsonl", type=str, required=True)
    return parser.parse_args()


def _normalize_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "task_id": raw.get("task_id", ""),
        "instruction": raw.get("instruction", ""),
        "supervisor": raw.get("supervisor", {}),
        "app_descriptions": raw.get("app_descriptions", {}),
        "dataset_name": raw.get("dataset_name", ""),
        "difficulty": raw.get("difficulty"),
        "scenario_id": raw.get("scenario_id"),
    }


def main():
    args = parse_args()

    with open(args.input_json, "r", encoding="utf-8") as f:
        payload = json.load(f)

    records: List[Dict[str, Any]]
    if isinstance(payload, list):
        records = payload
    elif (
        isinstance(payload, dict)
        and "records" in payload
        and isinstance(payload["records"], list)
    ):
        records = payload["records"]
    else:
        raise ValueError("Input JSON must be a list or {'records': [...]} format")

    out_dir = os.path.dirname(args.output_jsonl)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(args.output_jsonl, "w", encoding="utf-8") as out:
        for rec in records:
            out.write(json.dumps(_normalize_record(rec), ensure_ascii=True) + "\n")

    print(f"Wrote {len(records)} records to {args.output_jsonl}")


if __name__ == "__main__":
    main()
