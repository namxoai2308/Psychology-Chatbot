# Figure Generation Prompts

This file maps each report figure placeholder to a copy-ready prompt for GPT or another AI image tool. Use these prompts to generate clean thesis figures, then save the final assets under `report/figures/`.

## Global Style Prefix

Use this prefix before every prompt:

```text
Create a clean academic thesis figure in flat vector style, white background, 16:9 landscape, readable in an A4 PDF. Use restrained colors: navy for therapist core, teal for clinical logic, amber for peer support, red only for safety, gray for infrastructure. Use short English labels, no long paragraphs, no cartoons, no stock photos, no logos, no fake data, no decorative gradients. Make the layout structured, professional, and suitable for a computer science thesis.
```

For Chapter 4 result figures, use only real benchmark numbers from benchmark artifacts. If real scores are unavailable, generate a labeled template only.

---

## Chapter 3: Methodology Figures

### Figure 3.1: Therapist-Led Virtual Group Therapy Overview

- LaTeX label: `fig:system_architecture`
- Suggested file: `report/figures/fig_3_1_system_architecture.png`

```text
Create a system overview diagram titled "Therapist-Led Virtual Group Therapy Overview". Put "Therapist Core" in the center as the main authority. Inside it show: Screening, Evidence Extraction, Route Contracts, Stage FSM, Case Formulation, Stage Knowledge, Therapist Planning. Behind it place a large "Blackboard State" layer. Around the blackboard place "Nam: Universality / Catharsis" and "Chi Linh: Hope / Interpersonal Learning" as observer peer agents. After the therapist output, show Response Validation, Safety Critics, Visible Memory, and VSM Benchmark Logs. Make it clear that Nam and Linh only draft; the therapist approves final output.
```

### Figure 3.2: Evidence Extraction and Stage FSM Pipeline

- LaTeX label: `fig:evidence_fsm`
- Suggested file: `report/figures/fig_3_2_evidence_fsm.png`

```text
Create a clean draw.io-style technical diagram titled "Evidence-Gated Stage Control". Make it look like a manually designed architecture diagram, not a colorful presentation slide.

Style constraints:
- White background.
- Thin dark-gray borders.
- Very light fills only: near-white, pale blue, pale teal, pale amber, pale purple.
- No gradients, no shadows, no glossy effects, no large icons, no decorative illustrations.
- Use simple rectangles, small diamonds, circles, arrows, and swimlane-like grouping.
- Use 1 accent color per module at most; keep most text dark gray or navy.
- Use compact labels; avoid paragraphs.

Layout:
Use a left-to-right flow with five simple modules:

1. Context Input
   Include three small bullet rows:
   - user_message
   - recent_history
   - previous_stage

2. Evidence Extractor
   Put three small stacked rows inside:
   - CBT cues
   - MBI cues
   - BA cues
   Add a tiny note: "observable cues only"

3. Evidence Repair
   Show a vertical checklist:
   - schema check
   - normalize fields
   - reject unsupported inference
   - heuristic fallback
   Then a small diamond: "valid evidence?"
   PASS arrow continues to FSM.
   FAIL arrow stops with label "stay / fallback".

4. Stage FSM
   Draw five small stage nodes connected as a finite-state machine.
   On the side, show transition labels:
   STAY
   ADVANCE
   REGRESS
   RESET
   Add small note: "rules decide stage"

5. Stage Decision Record
   Show a code-card style output:
   previous_stage
   current_stage
   transition
   confidence
   evidence
   stage_goal
   required_yalom_factors

Add two thin secondary arrows:
- Stage Decision Record -> Context Input, labeled "next turn memory"
- Stage Decision Record -> Therapist Plan + Peer Policy

Bottom annotation:
"LLM extracts evidence; FSM controls progression."

Important:
Make it sparse, geometric, and draw.io-like. Do not use big title typography, colorful headers, complex icons, or infographic styling.
```

### Figure 3.3: Therapist Core Pipeline

- LaTeX label: `fig:therapist_core`
- Suggested file: `report/figures/fig_3_3_therapist_core.png`

```text
Create a therapist reasoning pipeline titled "Therapist Core Pipeline". Show the sequence: DASS-21 Onboarding -> Route Selection -> Evidence Extraction -> Route Contract Lookup -> Stage FSM -> Case Formulation -> Stage Knowledge + Style Card -> Therapist Plan -> Final Therapist Response. Add a red bypass arrow from Crisis Detection directly to Crisis-Safe Response, skipping normal stage work and peers. Emphasize that the therapist response is the final user-facing clinical voice.
```

### Figure 3.4: Blackboard Coordination Graph

- LaTeX label: `fig:blackboard_graph`
- Suggested file: `report/figures/fig_3_4_blackboard_graph.png`

```text
Create a graph diagram titled "Blackboard Coordination Graph". Put "Shared Blackboard State" in the center. Around it place LangGraph-style nodes: Onboarding, Clinical Assessor, Blackboard Peer Nam, Blackboard Peer Linh, Therapist Orchestrator, Guardrails, Memory Updater, Crisis Node, END. Show normal flow: Onboarding -> Clinical Assessor -> Nam/Linh observe -> Therapist Orchestrator -> Guardrails -> Memory Updater -> END. Show Crisis Node bypassing peer observers and going to Memory Updater. Use arrows to show all modules read/write the blackboard.
```

### Figure 3.5: Peer Contribution Decision Flow

- LaTeX label: `fig:peer_support_flow`
- Suggested file: `report/figures/fig_3_5_peer_support_flow.png`

```text
Create a decision-flow diagram titled "Peer Contribution Decision Flow". Start with Blackboard State, then split into Nam and Chi Linh observer lanes. Each lane checks: Required Yalom Factor, Current Stage, Persona Rules, Safety State, Repetition Risk. Output either NO_CONTRIBUTION or DRAFT. Send DRAFT to Therapist Approval with three possible actions: Include, Rewrite, Discard. Make silence look like a valid skill, not a failure. Show Nam mapped to Universality/Catharsis and Chi Linh mapped to Hope/Interpersonal Learning.
```

### Figure 3.6: Safety and Benchmark Trace Pipeline

- LaTeX label: `fig:safety_trace`
- Suggested file: `report/figures/fig_3_6_safety_trace.png`

```text
Create a safety pipeline titled "Safety and Benchmark Trace Pipeline". Show Final Candidate Response entering Response Validator, Supervisor Audit, and Psychosocial Safety Critics. Safety critics should include: Crisis, Medical Boundary, Dependency, Manipulation / Over-Agreement, Privacy / Bias. If high risk, route to Crisis or Boundary Fallback. If safe, route to Approved Output and Visible Memory. In parallel, send internal-only data to VSM Benchmark Logs: route, stage, evidence, peer decisions, therapist plan, validator result, safety flags, fallback_used. Mark discarded peer drafts and internal plans as "internal only".
```

---

## Chapter 4: Evaluation Figures

### Figure 4.1: VSM Hybrid Evaluation Pipeline

- LaTeX label: `fig:vsm_pipeline`
- Suggested file: `report/figures/fig_4_1_vsm_pipeline.png`

```text
Create a benchmark pipeline diagram titled "VSM Hybrid Evaluation Pipeline". Show: VSM Dataset -> System Inference -> Response Files -> Deterministic Checks -> LLM Judge -> Human Audit Sample -> Aggregation -> Confidence Intervals -> Report Tables and Figures. Add a side note that internal metadata is used only for ours_multi_agent, while baselines are judged from visible text. Use a clean research evaluation style, not a product dashboard.
```

### Figure 4.2: VSM Dataset Composition

- LaTeX label: `fig:vsm_composition`
- Suggested file: `report/figures/fig_4_2_vsm_composition.png`

```text
Create a dataset composition chart titled "VSM Dataset Composition". Use real split counts: Probe = 25 cases / 100 turns, Session-Core = 100 cases / 1200 turns, Stress = 17 cases / 306 turns, VSM-All = 142 cases / 1606 turns. Show route composition with CBT, MBI, BA, Safety, Yalom. For Session-Core use CBT 30, MBI 20, BA 20, Safety 15, Yalom 15. For Probe use 5 cases per route. For Stress use CBT 5, MBI 3, BA 3, Safety 3, Yalom 3. Prefer stacked bars or grouped bars with exact labels.
```

### Figure 4.3: Overall VSM Radar Chart

- LaTeX label: `fig:vsm_radar`
- Suggested file: `report/figures/fig_4_3_vsm_radar.png`

```text
Create a radar chart titled "Overall VSM Benchmark Profile". Use these dimensions: Clinical Safety, Therapeutic Quality, Modality Fidelity, Group Therapy Dynamics, Conversation Progress, System Reliability, Runtime Efficiency. Compare systems: base_model, prompt_1_1, seallm, camel_cbt, ours_multi_agent. Do not invent scores. If scores are not provided, create an empty radar chart template with dimension labels and legend only. If score_summary.csv is provided, plot actual values only.
```

### Figure 4.4: Route-Level Performance Comparison

- LaTeX label: `fig:route_performance`
- Suggested file: `report/figures/fig_4_4_route_performance.png`

```text
Create a grouped bar chart titled "Route-Level Benchmark Performance". Horizontal categories: CBT, MBI, BA, Safety, Yalom. Bars compare base_model, prompt_1_1, seallm, camel_cbt, ours_multi_agent. Use actual route-level scores if provided. Do not invent values. Use clear legend, readable labels, and muted colors. The purpose is to show whether each system performs consistently across therapy routes and safety/group cases.
```

### Figure 4.5: Safety and Adversarial Robustness Heatmap

- LaTeX label: `fig:safety_heatmap`
- Suggested file: `report/figures/fig_4_5_safety_heatmap.png`

```text
Create a heatmap titled "Safety and Adversarial Robustness". Rows: Crisis, Self-Harm, Medication Boundary, Dependency, Privacy, Unsafe Advice. Columns: base_model, prompt_1_1, seallm, camel_cbt, ours_multi_agent. Cell values should be pass rate or violation count from real benchmark results. Do not invent values. Use green for safer/pass, red for unsafe/violation. Include a small legend explaining the scale.
```

### Figure 4.6: Yalom Group Dynamics

- LaTeX label: `fig:yalom_dynamics`
- Suggested file: `report/figures/fig_4_6_yalom_dynamics.png`

```text
Create a focused bar chart titled "Yalom-Inspired Group Dynamics". This figure is mainly for ours_multi_agent. Show: Universality Match, Catharsis Match, Hope Match, Interpersonal Learning Match, Peer Silence Accuracy, Repetition Penalty. Use actual benchmark values if provided. If values are not provided, create a labeled template only. Use Nam color for Universality/Catharsis and Chi Linh color for Hope/Interpersonal Learning. Make clear that peer silence is a positive control signal.
```

### Figure 4.7: Quality-Latency Trade-Off

- LaTeX label: `fig:quality_latency`
- Suggested file: `report/figures/fig_4_7_quality_latency.png`

```text
Create a scatter plot titled "Quality-Latency Trade-Off". Horizontal label: Average Latency. Vertical label: VSM Total Score. Points: base_model, prompt_1_1, seallm, camel_cbt, ours_multi_agent. Point size represents token or serving cost if available. Use actual measured latency and score only; do not invent values. Add light grid lines and direct labels near each point.
```

---

## Usage Notes

- Chapter 3 figures are conceptual system diagrams and can be generated immediately.
- Chapter 4 figures should use real benchmark values when available.
- Do not include fabricated scores in the thesis. Use empty templates until scoring is complete.
- Keep figure text in English to match the report.
- After generating a figure, save it to the suggested path and replace the corresponding placeholder in `report/chapters/chapter3.tex` or `report/chapters/chapter4.tex`.
