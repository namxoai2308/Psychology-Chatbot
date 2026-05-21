from __future__ import annotations

import json
import random
from typing import Literal

from pydantic import BaseModel, Field

from ai_engine.blackboard.schemas import PeerContributionDecision, PeerDraft


class PeerContribution(BaseModel):
    decision: str = Field(default="NO_CONTRIBUTION")
    contribution_type: str = Field(default="NONE")
    therapeutic_function: str = Field(default="")
    yalom_factor: str = Field(default="NONE")
    text: str = Field(default="")
    reason: str = Field(default="")
    confidence: float = Field(default=0.0)
    safety_risk: bool = Field(default=False)


def no_contribution(
    *,
    sender: Literal["peer_mirror_agent", "veteran_peer_agent"],
    reason: str,
    yalom_factor: str = "NONE",
    confidence: float = 1.0,
    safety_risk: bool = False,
) -> dict:
    return {
        "peer_contribution_decisions": [
            PeerContributionDecision(
                sender=sender,
                decision="NO_CONTRIBUTION",
                reason=reason,
                yalom_factor=yalom_factor,
                confidence=confidence,
                safety_risk=safety_risk,
            ).model_dump()
        ]
    }


def parse_peer_contribution(raw_text: str, *, sender: str) -> PeerContribution:
    try:
        return PeerContribution.model_validate_json(raw_text)
    except Exception:
        try:
            return PeerContribution.model_validate(json.loads(raw_text))
        except Exception:
            return PeerContribution(
                decision="NO_CONTRIBUTION",
                reason=f"{sender} did not return valid blackboard contribution JSON.",
                confidence=0.0,
                safety_risk=True,
            )


def contribution_update(
    *,
    sender: Literal["peer_mirror_agent", "veteran_peer_agent"],
    contribution: PeerContribution,
    default_type: str,
    default_factor: str,
) -> dict:
    decision = str(contribution.decision or "NO_CONTRIBUTION").upper()
    decision_record = PeerContributionDecision(
        sender=sender,
        decision="CONTRIBUTE" if decision == "CONTRIBUTE" else "NO_CONTRIBUTION",
        reason=contribution.reason,
        yalom_factor=contribution.yalom_factor or default_factor,
        confidence=contribution.confidence,
        safety_risk=contribution.safety_risk,
    ).model_dump()

    if decision != "CONTRIBUTE" or contribution.safety_risk or not contribution.text.strip():
        return {"peer_contribution_decisions": [decision_record]}

    draft = PeerDraft(
        sender=sender,
        contribution_type=contribution.contribution_type or default_type,
        therapeutic_function=contribution.therapeutic_function or _default_therapeutic_function(sender, contribution.yalom_factor or default_factor),
        yalom_factor=contribution.yalom_factor or default_factor,
        text=contribution.text.strip(),
        reason=contribution.reason,
        confidence=contribution.confidence or 0.7,
        safety_risk=False,
        typing_time_ms=int(random.uniform(4000, 8000)),
    ).model_dump()
    return {"peer_drafts": [draft], "peer_contribution_decisions": [decision_record]}


def _default_therapeutic_function(sender: str, yalom_factor: str) -> str:
    if sender == "peer_mirror_agent":
        return "emotional_mirroring_and_shame_reduction"
    if yalom_factor == "Interpersonal Learning":
        return "brief_lived_experience_for_interpersonal_learning"
    return "realistic_hope_witness"
