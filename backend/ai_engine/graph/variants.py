from __future__ import annotations

from enum import Enum


class SystemVariant(str, Enum):
    OURS_FULL = "ours_full"
    OURS_NO_PEER = "ours_no_peer"
    OURS_NO_VALIDATOR = "ours_no_validator"
    OURS_NO_SAFETY_CRITIC = "ours_no_safety_critic"
    SINGLE_AGENT_STAGE_PROMPT = "single_agent_stage_prompt"
    SINGLE_AGENT_PLAIN = "single_agent_plain"


def normalize_system_variant(value: str | SystemVariant | None) -> SystemVariant:
    if isinstance(value, SystemVariant):
        return value
    try:
        return SystemVariant(value or SystemVariant.OURS_FULL.value)
    except ValueError as exc:
        allowed = ", ".join(variant.value for variant in SystemVariant)
        raise ValueError(f"Unknown system_variant '{value}'. Allowed values: {allowed}") from exc


def variant_flags(variant: str | SystemVariant | None) -> dict[str, bool | str]:
    normalized = normalize_system_variant(variant)
    single_agent = normalized in {SystemVariant.SINGLE_AGENT_STAGE_PROMPT, SystemVariant.SINGLE_AGENT_PLAIN}
    return {
        "system_variant": normalized.value,
        "variant": normalized.value,
        "peer_enabled": normalized == SystemVariant.OURS_FULL
        or normalized == SystemVariant.OURS_NO_VALIDATOR
        or normalized == SystemVariant.OURS_NO_SAFETY_CRITIC,
        "validator_enabled": normalized != SystemVariant.OURS_NO_VALIDATOR and not single_agent,
        "safety_critic_enabled": normalized != SystemVariant.OURS_NO_SAFETY_CRITIC,
    }
