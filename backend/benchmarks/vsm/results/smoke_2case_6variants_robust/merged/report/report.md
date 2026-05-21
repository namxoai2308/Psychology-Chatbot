# VSM Benchmark Report

## Evaluation Groups

- **Clinical Safety** (`clinical_safety`)
- **Therapeutic Quality** (`therapeutic_quality`)
- **Modality Fidelity** (`modality_fidelity`)
- **Group Therapy Dynamics** (`group_therapy_dynamics`)
- **Conversation Progress** (`conversation_progress`)
- **System Reliability** (`system_reliability`)
- **Runtime Efficiency** (`runtime_efficiency`)

## Table 1. Overall Benchmark Leaderboard

| System | VSM Total | Clinical Safety | Therapeutic Quality | Modality Fidelity | Group Therapy Dynamics | Reliability | Fallback Rate | Avg Latency |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Ours Full | 98.5 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0% | 8.7s |
| Ours No Peer | 88.9 | 100.0 | 80.0 | 90.0 | N/A | 100.0 | 0.0% | 6.9s |
| Ours No Safety Critic | 87.9 | 80.0 | 80.0 | 80.0 | 80.0 | 100.0 | 0.0% | 8.1s |
| Ours No Validator | 84.6 | 80.0 | 73.3 | 70.0 | 80.0 | 100.0 | 0.0% | 8.2s |
| Single Agent Plain | 68.2 | 80.0 | 56.7 | 40.0 | N/A | 100.0 | 0.0% | 2.1s |
| Single Agent + Stage | 86.3 | 100.0 | 80.0 | 80.0 | N/A | 100.0 | 0.0% | 4.7s |

## Table 2. Route-Level Performance

| System | Route | Cases | Stage Accuracy | Technique Fidelity | Route Bleed Count | Validator Pass | Fallback Rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Ours Full | CBT | 2 | 100.0 | 66.7 | 0 | 100.0 | 0.0% |
| Ours No Peer | CBT | 2 | 100.0 | 75.0 | 0 | 100.0 | 0.0% |
| Ours No Safety Critic | CBT | 2 | 100.0 | 75.0 | 0 | 100.0 | 0.0% |
| Ours No Validator | CBT | 2 | 100.0 | 75.0 | 0 | 100.0 | 0.0% |
| Single Agent Plain | CBT | 2 | 0.0 | 37.5 | 0 | 100.0 | 0.0% |
| Single Agent + Stage | CBT | 2 | 100.0 | 70.8 | 0 | 100.0 | 0.0% |

## Table 3. Safety and Adversarial Robustness

| System | Crisis Safe Response | Unsafe Advice Violation | Medical Boundary | Dependency Boundary | Adversarial Pass Rate | Safety Gate Failures |
| --- | --- | --- | --- | --- | --- | --- |
| Ours Full | N/A | 0 | N/A | 100.0 | 100.0 | 0 |
| Ours No Peer | N/A | 0 | N/A | 100.0 | 100.0 | 0 |
| Ours No Safety Critic | N/A | 0 | N/A | 100.0 | 100.0 | 0 |
| Ours No Validator | N/A | 0 | N/A | 100.0 | 100.0 | 0 |
| Single Agent Plain | N/A | 0 | N/A | 100.0 | 100.0 | 0 |
| Single Agent + Stage | N/A | 0 | N/A | 100.0 | 100.0 | 0 |

## Table 4. Yalom Group Dynamics

| System | Peer Selection Accuracy | Yalom Factor Match | Nam Persona Validity | Linh Persona Validity | Peer Silence Accuracy | Repetition Penalty |
| --- | --- | --- | --- | --- | --- | --- |
| Ours Full | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 |
| Ours No Peer | 0.0 | 0.0 | 0.0 | 0.0 | 100.0 | 100.0 |
| Ours No Safety Critic | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 |
| Ours No Validator | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 |
| Single Agent Plain | 0.0 | 0.0 | 0.0 | 0.0 | 100.0 | 100.0 |
| Single Agent + Stage | 0.0 | 0.0 | 0.0 | 0.0 | 100.0 | 100.0 |

## Table 5. Failure Taxonomy

| Failure Type | ours_full | ours_no_peer | ours_no_safety_critic | ours_no_validator | single_agent_plain | single_agent_stage_prompt |
| --- | --- | --- | --- | --- | --- | --- |
| exception | 0 | 0 | 0 | 0 | 0 | 0 |
| fallback_used | 0 | 0 | 0 | 0 | 0 | 0 |
| generic_response | 0 | 0 | 0 | 0 | 0 | 0 |
| hard_fail | 0 | 0 | 0 | 0 | 0 | 0 |
| peer_capability_absent | 0 | 8 | 0 | 0 | 8 | 8 |
| route_bleed | 0 | 0 | 0 | 0 | 0 | 0 |
| stage_mismatch | 0 | 0 | 0 | 0 | 0 | 0 |
| unsafe_advice | 0 | 0 | 0 | 0 | 0 | 0 |
| wrong_peer | 0 | 0 | 0 | 0 | 0 | 0 |

## Table 6. Confidence Intervals

| System | Metric | Mean | Std | 95% CI Low | 95% CI High | Turns |
| --- | --- | --- | --- | --- | --- | --- |
| Ours Full | final_hybrid_score | 98.5 | 2.1 | 97.8 | 99.4 | 24 |
| Ours No Peer | final_hybrid_score | 88.9 | 4.5 | 87.1 | 90.7 | 24 |
| Ours No Safety Critic | final_hybrid_score | 87.9 | 1.9 | 87.0 | 88.6 | 24 |
| Ours No Validator | final_hybrid_score | 84.6 | 3.5 | 83.2 | 86.0 | 24 |
| Single Agent Plain | final_hybrid_score | 68.2 | 3.8 | 66.7 | 69.7 | 24 |
| Single Agent + Stage | final_hybrid_score | 86.3 | 3.8 | 84.7 | 87.8 | 24 |

## Table 7. Human Audit Status

| Audit File | Audited Turns | Safety Agreement | Technique Agreement | Empathy Agreement |
| --- | --- | --- | --- | --- |
| human_audit_template.csv | 0 | Pending | Pending | Pending |

## Table 8. Ablation Deltas

| Baseline | Variant | Final Hybrid Δ | Clinical Safety Δ | Technique Fidelity Δ | Group Dynamics Δ | Latency Δ |
| --- | --- | --- | --- | --- | --- | --- |
| Ours Full | Ours No Peer | 9.6 | 0.0 | 10.0 | N/A | -1.8s |
| Ours Full | Ours No Safety Critic | 10.6 | 20.0 | 20.0 | 20.0 | -0.5s |
| Ours Full | Ours No Validator | 13.9 | 20.0 | 30.0 | 20.0 | -0.5s |
| Ours Full | Single Agent Plain | 30.3 | 20.0 | 60.0 | N/A | -6.6s |
| Ours Full | Single Agent + Stage | 12.2 | 0.0 | 20.0 | N/A | -4.0s |

## Figures

### Fig 1 Overall Radar

![Fig 1 Overall Radar](figures/fig_1_overall_radar.png)

### Fig 2 Route Grouped Bar

![Fig 2 Route Grouped Bar](figures/fig_2_route_grouped_bar.png)

### Fig 3 Safety Heatmap

![Fig 3 Safety Heatmap](figures/fig_3_safety_heatmap.png)

### Fig 4 Yalom Dynamics

![Fig 4 Yalom Dynamics](figures/fig_4_yalom_dynamics.png)

### Fig 5 Failure Stacked Bar

![Fig 5 Failure Stacked Bar](figures/fig_5_failure_stacked_bar.png)

### Fig 6 Fallback By Stage

![Fig 6 Fallback By Stage](figures/fig_6_fallback_by_stage.png)

### Fig 7 Cost Latency Scatter

![Fig 7 Cost Latency Scatter](figures/fig_7_cost_latency_scatter.png)

## Generated Files

- `tables/table_1_overall_leaderboard.csv`
- `tables/table_2_route_performance.csv`
- `tables/table_3_safety.csv`
- `tables/table_4_yalom_group.csv`
- `tables/table_5_failure_taxonomy.csv`
- `tables/table_6_confidence_intervals.csv`
- `tables/table_7_human_audit.csv`
- `tables/table_8_ablation_deltas.csv`