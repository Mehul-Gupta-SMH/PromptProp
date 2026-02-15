# Development Setup

## Prerequisites
- Python 3.10+
- Node.js 18+
- Git
- At least one LLM API key

## Clone & Install

```bash
git clone <repo-url>
cd PromptProp

# Backend
cd ppBackend
python -m venv ../.venv
source ../.venv/bin/activate  # or ..\.venv\Scripts\activate on Windows
pip install -r ../requirements.txt

# Frontend
cd ../ppFrontend
npm install
```

## Environment Variables

Set API keys as environment variables:
```bash
export GEMINI_API_KEY=your-key-here
export OPENAI_API_KEY=your-key-here      # optional
export ANTHROPIC_API_KEY=your-key-here   # optional
```

Or create a `.env` file in the project root (it's gitignored).

## Running

Terminal 1 (Backend):
```bash
cd ppBackend
python main.py
# http://localhost:8000
# Swagger docs: http://localhost:8000/docs
```

Terminal 2 (Frontend):
```bash
cd ppFrontend
npm run dev
# http://localhost:3000
```

## Project Structure
```
PromptProp/
├── ppBackend/
│   ├── main.py              # Server entry point
│   ├── route.py             # API endpoints
│   ├── llm/                 # LiteLLM wrapper
│   ├── prompts/             # Role definitions
│   ├── ppsecrets/           # API key management
│   ├── configs/             # YAML configs (dev/prod)
│   └── resources/           # MLflow metrics
├── ppFrontend/
│   ├── App.tsx              # Main React component
│   ├── services/            # API client
│   ├── components/          # UI components
│   └── types.ts             # TypeScript types
├── docs/                    # Documentation (wiki pages)
├── requirements.txt         # Python dependencies
└── README.md
```

## Configuration
- Backend config: `ppBackend/configs/dev.yaml` / `prod.yaml`
- Set environment: `export ppENV=dev` (default) or `export ppENV=prod`
