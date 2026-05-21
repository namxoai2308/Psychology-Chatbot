from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


def read_prompt(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return f"<Lỗi: Không tìm thấy file {path.name}>"


@dataclass(frozen=True)
class PromptPack:
    triage_dispatcher: str
    therapist_cbt: str
    therapist_mbi: str
    therapist_ba: str
    crisis: str
    analyzer_core: str
    orchestrator: str
    peer_mirror: str
    veteran_peer: str
    cbt_stages: dict[str, str]
    mbi_stages: dict[str, str]
    ba_stages: dict[str, str]


@lru_cache(maxsize=1)
def load_prompts() -> PromptPack:
    return PromptPack(
        triage_dispatcher=read_prompt(PROMPTS_DIR / "routers" / "dispatcher.txt"),
        therapist_cbt=read_prompt(PROMPTS_DIR / "system_personas" / "therapist_cbt.txt"),
        therapist_mbi=read_prompt(PROMPTS_DIR / "system_personas" / "therapist_mbi.txt"),
        therapist_ba=read_prompt(PROMPTS_DIR / "system_personas" / "therapist_ba.txt"),
        analyzer_core=read_prompt(PROMPTS_DIR / "system_personas" / "analyzer_core.txt"),
        orchestrator=read_prompt(PROMPTS_DIR / "group_therapy" / "orchestrator.txt"),
        peer_mirror=read_prompt(PROMPTS_DIR / "group_therapy" / "peer_mirror.txt"),
        veteran_peer=read_prompt(PROMPTS_DIR / "group_therapy" / "veteran_peer.txt"),
        crisis=read_prompt(PROMPTS_DIR / "safety_protocols" / "crisis_intervention.txt"),
        cbt_stages={
            "stage_1_venting": read_prompt(PROMPTS_DIR / "cbt_stages" / "stage_1_venting.txt"),
            "stage_2_abc_model": read_prompt(PROMPTS_DIR / "cbt_stages" / "stage_2_abc_model.txt"),
            "stage_3_distortions": read_prompt(PROMPTS_DIR / "cbt_stages" / "stage_3_distortions.txt"),
            "stage_4_socratic": read_prompt(PROMPTS_DIR / "cbt_stages" / "stage_4_socratic.txt"),
            "stage_5_action": read_prompt(PROMPTS_DIR / "cbt_stages" / "stage_5_action.txt"),
        },
        mbi_stages={
            "stage_1_grounding": read_prompt(PROMPTS_DIR / "mbi_stages" / "stage_1_grounding.txt"),
            "stage_2_decentering": read_prompt(PROMPTS_DIR / "mbi_stages" / "stage_2_decentering.txt"),
            "stage_3_body_scan": read_prompt(PROMPTS_DIR / "mbi_stages" / "stage_3_body_scan.txt"),
            "stage_4_mindful_action": read_prompt(PROMPTS_DIR / "mbi_stages" / "stage_4_mindful_action.txt"),
        },
        ba_stages={
            "stage_1_energy_check": read_prompt(PROMPTS_DIR / "ba_stages" / "stage_1_energy_check.txt"),
            "stage_2_micro_action": read_prompt(PROMPTS_DIR / "ba_stages" / "stage_2_micro_action.txt"),
            "stage_3_barrier_schedule": read_prompt(PROMPTS_DIR / "ba_stages" / "stage_3_barrier_schedule.txt"),
            "stage_4_momentum_reward": read_prompt(PROMPTS_DIR / "ba_stages" / "stage_4_momentum_reward.txt"),
        },
    )


class PromptBundleProxy:
    def __getattr__(self, item: str):
        return getattr(load_prompts(), item)
