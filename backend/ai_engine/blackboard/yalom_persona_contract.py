from __future__ import annotations

from dataclasses import dataclass

from ai_engine.blackboard.ba_contract import is_ba_stage
from ai_engine.blackboard.cbt_contract import cbt_allowed_yalom, cbt_peer_allowed, has_any, normalize_text
from ai_engine.blackboard.mbi_contract import is_mbi_stage


@dataclass(frozen=True)
class PeerPolicyResult:
    allowed: bool
    reason: str


NAM_FACTORS = {"Universality", "Catharsis"}
LINH_FACTORS = {"Hope", "Interpersonal Learning"}


def route_peer_allowed(route: str, current_stage: str, sender: str, required_factors: list[str]) -> bool:
    if not required_factors or "NONE" in required_factors:
        return False
    route_key = (route or "CBT").upper()
    if route_key == "CBT":
        if not set(required_factors).issubset(cbt_allowed_yalom(current_stage)):
            return False
        return cbt_peer_allowed(current_stage, sender, required_factors)
    if route_key == "MBI":
        if sender == "peer_mirror_agent":
            return current_stage == "mbi_stage_1_grounding" and bool(NAM_FACTORS & set(required_factors))
        if sender == "veteran_peer_agent":
            return current_stage == "mbi_stage_4_mindful_action" and bool(LINH_FACTORS & set(required_factors))
    if route_key == "BA":
        if sender == "peer_mirror_agent":
            return current_stage in {"ba_stage_1_energy_check", "ba_stage_3_barrier_schedule"} and bool(
                NAM_FACTORS & set(required_factors)
            )
        if sender == "veteran_peer_agent":
            return current_stage in {"ba_stage_2_micro_action", "ba_stage_3_barrier_schedule", "ba_stage_4_momentum_reward"} and bool(
                LINH_FACTORS & set(required_factors)
            )
    return False


def validate_peer_contribution(
    *,
    route: str,
    current_stage: str,
    sender: str,
    required_factors: list[str],
    yalom_factor: str,
    text: str,
) -> PeerPolicyResult:
    if not route_peer_allowed(route, current_stage, sender, required_factors):
        return PeerPolicyResult(False, f"{sender} is not allowed for {route}/{current_stage} with factors {required_factors}.")
    if yalom_factor and yalom_factor != "NONE" and yalom_factor not in set(required_factors):
        return PeerPolicyResult(False, f"Peer factor {yalom_factor} is not in required factors {required_factors}.")
    if sender == "peer_mirror_agent":
        return _validate_nam(route, current_stage, text)
    if sender == "veteran_peer_agent":
        return _validate_linh(route, current_stage, text)
    return PeerPolicyResult(False, "Unknown peer sender.")


def _validate_nam(route: str, current_stage: str, text: str) -> PeerPolicyResult:
    normalized = normalize_text(text)
    if _word_count(normalized) > 55:
        return PeerPolicyResult(False, "Nam draft is too long for an emotional mirror.")
    forbidden = (
        "bằng chứng",
        "100%",
        "lỗi tư duy",
        "suy nghĩ tự động",
        "thảm họa hóa",
        "trắng đen",
        "đọc tâm trí",
        "dán nhãn",
        "em nên",
        "bạn nên",
        "cần phải",
        "phải làm",
    )
    if has_any(normalized, forbidden):
        return PeerPolicyResult(False, "Nam draft steals therapist technique or gives advice.")
    if current_stage in {"cbt_stage_4_socratic", "mbi_stage_2_decentering", "mbi_stage_3_body_scan"}:
        return PeerPolicyResult(False, f"Nam should stay silent in {current_stage}.")
    return PeerPolicyResult(True, "Nam draft fits emotional mirror / Universality-Catharsis role.")


def _validate_linh(route: str, current_stage: str, text: str) -> PeerPolicyResult:
    normalized = normalize_text(text)
    if _word_count(normalized) > 70:
        return PeerPolicyResult(False, "Linh draft is too long and may take the spotlight.")
    forbidden = (
        "em nên",
        "bạn nên",
        "hãy",
        "cần phải",
        "chắc chắn sẽ ổn",
        "mọi thứ sẽ ổn",
        "đừng buồn",
        "cứ cố lên",
    )
    if has_any(normalized, forbidden):
        return PeerPolicyResult(False, "Linh draft gives advice or toxic positivity.")
    if current_stage in {"cbt_stage_4_socratic", "mbi_stage_1_grounding", "mbi_stage_2_decentering", "mbi_stage_3_body_scan"}:
        return PeerPolicyResult(False, f"Linh should stay silent in {current_stage}.")
    if not (is_ba_stage(current_stage) or is_mbi_stage(current_stage) or current_stage.startswith("cbt_")):
        return PeerPolicyResult(False, "Unknown stage for Linh.")
    return PeerPolicyResult(True, "Linh draft fits Hope / Interpersonal Learning role.")


def _word_count(normalized_text: str) -> int:
    return len([word for word in normalized_text.split() if word])
