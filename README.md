# AgroVision AI

AgroVision AI is a web app for farmers. It combines a React frontend with a FastAPI backend to provide crop and farm guidance, image-based analysis, weather forecasts, and market information.

## How the project works

```text
Farmer
  -> React app (frontend/)
  -> FastAPI API (backend/)
       -> SQLite locally, or PostgreSQL when DATABASE_URL is configured
       -> Groq for AI-powered analysis and chat
       -> CEDA / data.gov.in for market data
       -> free weather providers for forecasts
```

### Main user workflow

1. A farmer creates an account or logs in. The backend verifies credentials and returns a JWT; the frontend uses it for authenticated features.
2. From the dashboard, the farmer can:
   - Upload a field photo and provide conditions for land and crop recommendations.
   - Upload a crop or leaf photo to check for possible disease and get prevention guidance.
   - Review harvest guidance based on a crop photo, weather, and forecast information.
   - Ask for market advice using crop, location, quantity, and available mandi price history.
   - Ask the farming chat assistant questions.
3. The frontend sends API requests to the backend. The backend reads or writes account data in the configured database and calls external providers as needed.

AI results and market/weather data depend on the availability and configuration of their external providers. Treat AI-generated agricultural guidance as informational and verify important treatment or selling decisions with a qualified local expert.

## Run locally on Windows

### 1. Configure the backend

Open PowerShell:

```powershell
cd C:\path\to\Agrovision-ai\backend
.\venv\Scripts\Activate.ps1
Copy-Item .env.example .env
```

Edit `backend/.env` and add the API keys you have. `GROQ_API_KEY` is needed for AI features; `CEDA_API_KEY` enables CEDA-backed market data. The data.gov.in integration can use `DATA_GOV_IN_API_KEY` or `DATA_GOV_API_KEY`. If you do not configure `DATABASE_URL`, the app uses a local SQLite database at `backend/agrovision.db`.

Install backend dependencies if needed, then run the API:

```powershell
pip install -r requirements.txt
uvicorn main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive API documentation is at `http://127.0.0.1:8000/docs`.

### 2. Run the frontend

In a second PowerShell window:

```powershell
cd C:\path\to\Agrovision-ai\frontend
npm install
npm run dev
```

Open the local URL printed by Vite. The frontend uses `http://127.0.0.1:8000` by default. To use a different backend URL, set `VITE_API_URL` in `frontend/.env` before starting Vite.

## Configuration and Git safety

- Keep real API keys and other credentials in local `.env` files or your hosting provider's environment settings. Never put secret values in source code or commit them.
- The root `.gitignore` excludes `.env` files. The checked-in `backend/.env.example` is a placeholder template and is safe to commit.
- If a secret has ever been committed, removing it from a later commit is not enough: revoke or rotate that key.
- The SQLite database and local virtual environment are also excluded from Git.

## Production notes

- Use a managed PostgreSQL database and set `DATABASE_URL` in the backend hosting environment.
- Set a strong, private JWT signing key through an environment variable before public deployment; do not use the development key currently in the backend.
- Configure CORS to allow only the deployed frontend origin instead of every origin.
- Set `VITE_API_URL` to the deployed backend URL and provide required API keys through the host's secret/environment-variable settings.
- Build the frontend with `npm run build` and deploy the generated `frontend/dist` directory with a static hosting service. Run the backend with an ASGI server such as Uvicorn.

## Repository layout

- `backend/` — FastAPI application, database configuration, external data integrations, and Python dependencies.
- `frontend/` — React/Vite application, pages, and UI components.
- `datasets/` — local data files; ignored by Git.
