# cbt-ai-therapist-project

Monorepo mẫu cho hệ thống CBT AI Therapist:
- `frontend/`: UI/UX (Next.js/React)
- `backend/`: FastAPI + AI engine
- `benchmark/`: đánh giá chất lượng (safety + CBT adherence)
- `data_knowledge/`: tài liệu CBT để làm RAG
- `observability/`: telemetry/tracing/logging

## Chạy nhanh

```bash
cd cbt-ai-therapist-project
docker compose up
```

Backend healthcheck: `GET /health` tại `http://localhost:8000/health`.

