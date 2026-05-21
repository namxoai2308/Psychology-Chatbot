# TRACE-VSM

An auditable Vietnamese student mental-health support dialogue system with multiple AI agents.

TRACE-VSM is a research prototype for support dialogue. It is not a clinical deployment and must not be used as a substitute for diagnosis, treatment, or crisis care.

## Benchmark Snapshot

Frozen benchmark: `VSM-Core` 

| System | Final | 95% CI |
| --- | ---: | --- |
| TRACE-Full | 89.68 | [89.09, 90.21] |
| TRACE-NoPeer | 86.00 | [85.53, 86.40] |
| TRACE-NoSafetyCritic | 85.54 | [84.97, 86.07] |
| TRACE-NoValidator | 82.69 | [82.12, 83.20] |
| Single-Agent Stage Prompt | 81.99 | [81.52, 82.42] |
| Prompt 1-1 | 77.94 | [77.19, 78.62] |
| Single-Agent Plain | 72.99 | [72.58, 73.38] |
| Base Model | 62.11 | [61.36, 62.89] |
| CAMEL-CBT | 48.99 | [48.45, 49.51] |
| SeaLLM | 44.22 | [43.79, 44.67] |

Secondary audits for TRACE-Full: CAPE-II transcript-adapted `85.83`; Yalom group dynamics `90.22`; peer selection / Yalom factor match `79.94 / 79.94`.


## Setup and Installation

1. Clone and navigate to project

```bash
git clone <repository-url>
cd trace-vsm
```

2. Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
# or .venv\Scripts\activate   # Windows
```

3. Install backend dependencies

```bash
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

4. Set API key

Create a `.env` file in the project root. Use one provider, or add multiple keys if you want to switch models in the UI.

```text
# DeepSeek
DEEPSEEK_API_KEY=your_deepseek_api_key

# GPT / OpenAI
OPENAI_API_KEY=your_openai_api_key
# optional: OPENAI_MODEL=gpt-4o-mini

# Gemini
GOOGLE_API_KEY=your_google_api_key
# or GEMINI_API_KEY=your_gemini_api_key
```

## Run Application

1. Start backend

```bash
PYTHONPATH=backend uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Backend health check:

```text
http://127.0.0.1:8000
```

2. Start frontend

```bash
cd frontend
npm install
npm run dev
```

Access the application at:

```text
http://127.0.0.1:3000
```
