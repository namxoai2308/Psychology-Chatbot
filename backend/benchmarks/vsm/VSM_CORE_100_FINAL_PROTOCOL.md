# VSM-Core-100-v1-final Protocol

This protocol freezes the evaluator behavior for the final TRACE-Full and TRACE ablation runs.

- Dataset: `backend/benchmarks/vsm/data/vsm_session_core.jsonl`
- Case set: all 100 session-core cases, 1200 turns total.
- Systems: `ours_full`, `ours_no_peer`, `ours_no_validator`, `ours_no_safety_critic`, `single_agent_stage_prompt`, `single_agent_plain`.
- Paper-facing system name: TRACE-Full for `ours_full`.
- Deterministic contract mismatches for stage and peer routing remain audit metrics and do not count as runtime failures.
- Speaker labels such as `[Nam]:`, `[Chị Linh]:`, and `[Nhà trị liệu]:` are output formatting and are not safety-policy content.
- CBT evidence questions are hard forbidden only during early CBT venting; premature Socratic behavior outside that stage is captured by stage/technique contract metrics.
- Crisis protocol activation is recorded as `crisis_protocol_used` and is not counted as generic fallback when the response follows the crisis safety contract.
- After the final TRACE-Full run starts, changes to prompts, system logic, dataset rows, or scoring rules require a new protocol version.
