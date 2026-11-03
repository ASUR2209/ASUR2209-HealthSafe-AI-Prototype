# HealthSafe AI

Scans a food product's ingredients against a person's health conditions and medicines.
A personalised rule engine, an XGBoost classifier (`ml/healthsafe_model_v6.pkl`) and an
ingredient heuristic each score the product; the web app shows what each layer found.

**Live:** https://dheer46.github.io/ASUR2209-HealthSafe-AI-Prototype/

The hosted app runs the whole pipeline in the browser: the same XGBoost model, rule
engine and heuristic (verified identical to the Flask backend on 1,894 inputs), label OCR
with Tesseract compiled to WebAssembly, and barcode lookups straight from Open Food Facts.
Household accounts are kept in that browser's local storage. It deploys from `main` via
`.github/workflows/pages.yml`.

After retraining the model or editing the rules in `backend/app.py`, re-export them for
the browser:

```bash
.venv/Scripts/python ml/export_browser_model.py
```

## Run locally

Needs Python 3.11+, Node 18+, and [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
installed at `C:\Program Files\Tesseract-OCR` for label-photo scans.

**1. Backend** (from the repo root)

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements.txt
.venv/Scripts/python backend/app.py
```

The API runs on http://localhost:5000.

**2. Frontend** (in a second terminal)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The top bar shows **Model online** when the frontend can reach the API.

## Layout

- `backend/` — Flask API: scan, OCR, barcode lookup, recommendations, household accounts
- `ml/` — trained model, evaluation script, and `export_browser_model.py`
- `frontend/` — React + Vite web app (see `frontend/README.md`); `frontend/src/engine/` is
  the in-browser copy of the backend
