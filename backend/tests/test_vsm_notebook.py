from __future__ import annotations

import json
import unittest
from pathlib import Path


class VSMNotebookTest(unittest.TestCase):
    def test_full_benchmark_notebook_is_valid_and_documents_core_flow(self) -> None:
        path = Path("backend/benchmarks/vsm/notebooks/vsm_full_benchmark.ipynb")
        notebook = json.loads(path.read_text(encoding="utf-8"))
        source = "\n".join(
            "".join(cell.get("source", []))
            for cell in notebook.get("cells", [])
        )

        self.assertEqual(4, notebook["nbformat"])
        self.assertIn("run_inference", source)
        self.assertIn("per_case_results.jsonl", source)
        self.assertIn("failure_table", source)
        self.assertIn("figures_from_notebook", source)
        self.assertIn('SYSTEMS = ["dry_run"]', source)


if __name__ == "__main__":
    unittest.main()
