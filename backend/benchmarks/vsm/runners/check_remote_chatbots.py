from __future__ import annotations

import argparse
import json

from benchmarks.vsm.adapters.remote_chatbots import healthcheck_remote_chatbot


def main() -> None:
    parser = argparse.ArgumentParser(description="Check standalone Kaggle ngrok endpoints.")
    parser.add_argument("--systems", default="seallm,camel_cbt")
    args = parser.parse_args()

    systems = [item.strip() for item in args.systems.split(",") if item.strip()]
    result = {system: healthcheck_remote_chatbot(system) for system in systems}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
