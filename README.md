# Government Scheme Recommender

A local Flask portfolio demo that helps people explore a curated catalogue of Indian public programmes through a guided conversation. The recommender is transparent and rule-based: it ranks possible matches using explicit fields in a CSV file. It does not use machine learning, an LLM, or automated eligibility determinations.

> **Important:** This is an informational prototype, not a government service and not a guarantee of eligibility, benefits, application acceptance, or current availability. Programme rules change. Verify every detail with the responsible department or official portal before applying. Do not enter Aadhaar numbers, bank details, passwords, or other sensitive identifiers.

## Features

- Guided, one-question-at-a-time conversation with optional skips
- Progressive collection of interests, age, state, gender, income, education, employment, occupation and voluntarily shared category
- CSV-backed catalogue with 100 distinct entries across education, jobs and skills, agriculture, women, healthcare, housing, financial assistance, social welfare and enterprise
- Transparent scoring, match reasons, explicit-rule filtering, and verification notes for unknown criteria
- Scheme cards with benefit summaries, eligibility status, application link and detailed information dialog
- Search catalogue API with category and keyword filters
- Responsive desktop/mobile layout, loading state, typing indicator, error/empty states, restart and conversational follow-ups
- No user profiles or conversation data are persisted by the application

## Technologies

Python 3.10+, Flask, Python standard-library `csv`, HTML, CSS and vanilla JavaScript. No database or frontend framework is required.

## Architecture

The Flask app serves the page and JSON API. `backend/chatbot.py` owns the conversational stages and input parsing. `backend/recommender.py` reads and validates the CSV, applies transparent eligibility checks and computes relative match scores. The browser renders chat and scheme cards and requests detail records from Flask. The catalogue is stored in `data/government_schemes.csv`.

## Project Structure

```text
government-scheme-recommender/
├── app.py
├── backend/
│   ├── __init__.py
│   ├── chatbot.py
│   └── recommender.py
├── data/
│   └── government_schemes.csv
├── static/
│   ├── css/style.css
│   └── js/script.js
├── templates/index.html
├── tests/
│   └── test_recommender.py
├── render.yaml
├── requirements.txt
└── README.md
```

## Installation (Windows / VS Code)

Open PowerShell in this project folder. Use Python 3.10 or newer.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, use the interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

In VS Code, select `.venv\Scripts\python.exe` with **Python: Select Interpreter**.

## Run

```powershell
python app.py
```

Open `http://127.0.0.1:5000`. Stop the local development server with `Ctrl+C`. Flask debug mode is enabled only for local development; do not expose this development server to the public internet.

## Deploy Online

GitHub stores the source code; it does not run this Flask application through GitHub Pages. For a live, working chatbot, deploy the repository as a Python web service on Render. The included `render.yaml` configures Gunicorn, the production WSGI server, and a health check.

1. Push this project to a GitHub repository.
2. In Render, choose **New** > **Blueprint** and connect the repository.
3. Review the service settings from `render.yaml` and create the service.
4. Open the public `onrender.com` URL shown by Render after deployment completes.

The first request may take longer on a free instance that has spun down. The local Flask development server is not used in production.

## Tests

```powershell
python -m unittest discover -s tests -v
```

Tests cover catalogue integrity, explicit age filtering, explanation metadata, input validation, the chat start route, scheme details and core API responses.

## API

All endpoints use JSON except `GET /`, which serves the application page.

### `GET /api/schemes`

Returns `{ "count": 100, "schemes": [...] }`. Optional query parameters: `category` for exact category filtering and `q` for a simple name/category/description search.

### `POST /api/recommend`

Request:

```json
{
  "profile": {
    "interests": ["Agriculture"],
    "age": 35,
    "state": "Maharashtra",
    "occupation": "Farmer"
  }
}
```

Allowed profile fields: `interests`, `age`, `state`, `gender`, `annual_income`, `education`, `employment_status`, `occupation`, and `category`. Values may be omitted. Returns `{ "count": n, "recommendations": [...] }`; invalid JSON shape or values return HTTP 400.

### `POST /api/chat`

Request fields: `message` (up to 500 characters), `profile` (object) and `stage` (conversation stage). Set `stage` to `start` and an empty message to begin. Each response contains `reply`, `stage`, `profile`, and question metadata (`input_type`, `options`, `optional`, `progress`) where applicable. When the intake completes, it also contains `recommendations`. Follow-up messages can ask why a match appears, request more results, or restart.

### `GET /api/scheme/<scheme_id>`

Returns `{ "scheme": {...} }`, or HTTP 404 when the ID is unknown.

## Dataset

`data/government_schemes.csv` contains 100 unique catalogue entries and these fields: scheme ID/name, department, category, description, eligibility criteria, min/max age, gender, income limit, state, education, occupation, benefits, process, URL, documents, verification status and source note.

The CSV is a manually curated demo catalogue, not a live feed or an independently audited official dataset. Scheme names, current status, departments and URLs can change. Scheme-specific details that have not been independently checked are marked `Unknown - verify`, with source notes identifying directory/department links versus validated scheme pages. Some catalogue entries are historical or umbrella programmes; their status is flagged. Official links are provided as starting points and must be checked before use. Do not infer eligibility or benefit amounts from an unknown field.

## Recommendation Methodology

The engine applies hard exclusions only when a supplied age, state, gender, education, occupation or category explicitly conflicts with a corresponding known catalogue rule. Missing or unknown rules are not treated as a match; the result includes a verification note instead. Relevant interest/category adds the largest score contribution; matching known criteria adds smaller contributions. A transparent relative match score ranks candidates. It is not a probability, confidence interval, benefit estimate or eligibility decision. The ranking is bounded to 50 entries per request.

## Screenshots

Screenshots can be added here after running the application locally.

## Limitations

- The catalogue is static, manually curated, and not a complete or official source of scheme data.
- Scheme eligibility, benefits, document lists, availability and application steps can vary by state, component and date; many fields explicitly require verification.
- Some entries are portals, umbrella programmes or historical programmes rather than currently open individual benefits.
- Text matching is literal and intentionally simple; it does not understand synonyms or languages beyond the entered text.
- The score is a rule-match ranking only. This prototype does not use ML, NLP, an LLM, user authentication or persistent storage.
- The local Flask development server is not hardened for production.

## Future Improvements

- Validate each catalogue row against dated scheme guidelines and store a reviewer/source URL per field.
- Add a safe, sourced update workflow and data freshness checks.
- Add state-specific verified catalogues and multilingual user-tested conversations.
- Improve controlled vocabularies, matching tests and accessible keyboard/screen-reader review.
- Deploy behind a production WSGI server with appropriate security, privacy and operational review.