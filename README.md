# DataBridge AI

DataBridge AI turns natural-language questions into reviewable, read-only SQL. Its uncertainty-aware router selects a local model or a configured API model, and the web app includes dataset upload, query history, follow-up questions, charts, and evaluation views.

## Requirements

- Python 3.10 or newer
- Node.js 18 or newer
- An API key from Groq, OpenAI, or Anthropic for custom natural-language questions

The replay demo and saved benchmark questions run without a GPU. A model-provider API key is only needed for questions that are not in the saved benchmark.

## Run locally

1. Install the Python app and development dependencies:

   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   python -m pip install -e ".[serve,dev]"
   ```

2. Optional: create a local `.env` file in the project root for custom questions. Set the provider and model you use, plus its API key. For example:

   ```text
   MODE=replay
   TEACHER_PROVIDER=groq
   TEACHER_MODEL=openai/gpt-oss-20b
   GROQ_API_KEY=your_key_here
   CORS_ORIGINS=http://localhost:5173
   ```

   Keep `.env` private; never publish API keys.

3. Start the backend from the project root:

   ```powershell
   python -m uvicorn sqlrouter.serve.main:app --host 127.0.0.1 --port 8000
   ```

4. In a second terminal, install and start the frontend:

   ```powershell
   cd frontend
   npm ci
   npm run dev
   ```

5. Open <http://localhost:5173>, create an account, and try a bundled dataset in the Playground.

## Optional ML dependencies

The web app does not install model-training libraries by default. For the training pipeline, install `python -m pip install -e ".[ml]"`. Live local-model serving also needs the server dependencies (`.[serve,ml]`), a compatible model and probe; see `configs/` and the pipeline scripts.

## Data and privacy

Bundled replay fixtures and four small demo databases are included. Accounts, uploaded datasets, query history, and feedback are runtime-local; do not publish them. Runtime account data is created in `artifacts/auth.sqlite`.

## Tests

```powershell
python -m pytest tests -q
cd frontend
npm run lint
npm run build
```
