# HealthSafe AI — web frontend

React + Vite frontend for the Flask API in `../backend`.

## Run

```bash
# 1. backend (from repo root)
python backend/app.py            # serves http://localhost:5000

# 2. frontend
cd web
npm install
npm run dev                      # http://localhost:5173
```

The dev server proxies `/api/*` to `http://127.0.0.1:5000`. Point it elsewhere with
`HEALTHSAFE_API=http://host:port npm run dev`, or build against a deployed API with
`VITE_API_URL=https://api.example.com npm run build`.

If the API is down, typed-ingredient scans fall back to a small in-browser rule set
(marked "demo engine" in the readout). Photo, barcode, alternatives and household
need the backend. Photo scans also need Tesseract at `C:\Program Files\Tesseract-OCR`.

## Layout

- `src/Lightbox.tsx` — the readout: one well per ingredient, one lane per pipeline layer
  (personal rules, ingredient heuristic, XGBoost).
- `src/Composer.tsx` — typed text, label photo (`/ocr/analyze`), barcode (`/scan-barcode`).
- `src/ProfilePanel.tsx` — conditions and medicines sent as `user_profile`.
- `src/Findings.tsx` — flags, medicine conflicts, alternatives (`/recommend`).
- `src/Household.tsx` — `/family/*` register, login, dashboard, members.
- `src/api.ts` — API client and response normalisation.
