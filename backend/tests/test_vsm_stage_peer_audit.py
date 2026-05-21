from __future__ import annotations

import unittest

from benchmarks.vsm.runners.audit_stage_peer_contract import audit_dataset


class VSMStagePeerAuditTests(unittest.TestCase):
    def test_session_core_deterministic_stage_peer_contract_is_stable(self) -> None:
        summary = audit_dataset("backend/benchmarks/vsm/data/vsm_session_core.jsonl")

        self.assertEqual(summary["turn_count"], 1200)
        self.assertLessEqual(summary["stage_mismatch_count"], 1)
        self.assertLessEqual(summary["peer_mismatch_count"], 1)
        self.assertEqual(summary["stage_by_group"], {"cbt_dialogues": 1})
        self.assertEqual(summary["peer_by_group"], {"cbt_dialogues": 1})


if __name__ == "__main__":
    unittest.main()
