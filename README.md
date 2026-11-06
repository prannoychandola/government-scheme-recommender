# 🏛️ Government Scheme Recommender

### A transparent, CSV-backed chatbot for exploring Indian public programmes

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-REST%20API-000000?logo=flask&logoColor=white)
![Data](https://img.shields.io/badge/Data-CSV-2E7D32)
![Matching](https://img.shields.io/badge/Matching-Rule--based-D98A32)

**[Open the live chatbot](https://government-scheme-recommender.onrender.com/)** · **[View the GitHub repository](https://github.com/prannoychandola/government-scheme-recommender)**

> **Important:** This is an independent informational prototype, not a government service and not an eligibility decision. Scheme rules and availability can change. Verify details with the responsible department before applying. Never enter Aadhaar numbers, bank details, passwords, or other sensitive identifiers.

## 📖 Overview

Finding public assistance can mean navigating many separate programmes and eligibility rules. This project provides a conversational way to explore a curated catalogue of Indian government schemes. It asks for relevant details progressively, then ranks candidate schemes using transparent rules and the fields available in a CSV dataset.

The recommender is intentionally **rule-based**. It does not use machine learning, NLP, or an LLM, and it cannot confirm eligibility or guarantee benefits.

## ✨ Features

- 💬 Guided conversation that collects information one question at a time
- ⏭️ Optional questions can be skipped
- 🗺️ Profile questions cover interests, age, state, gender, income, education, employment, occupation, and optionally shared category
- 🧾 CSV-backed catalogue of 100 distinct scheme entries across nine support areas
- ⚖️ Transparent ranking, match explanations, and explicit-rule exclusions
- 🔎 Unknown or unverified criteria are identified instead of guessed
- 🗂️ Scheme cards include benefits, eligibility notes, official links, and detailed views
- 🔌 JSON API for catalogue search, recommendations, conversation, and scheme details
- 📱 Responsive interface with loading, empty, validation-error, and restart states
- 🔒 No user profile or conversation data is persisted by the application

## 🛠️ Technology Stack

| Area | Technology |
| --- | --- |
| Language | Python 3.10+ |
| Backend | Flask |
| Data | CSV and Python standard-library `csv` module |
| Frontend | HTML5, CSS3, vanilla JavaScript |
| Production server | Gunicorn on Render |
| Tests | Python `unittest` |

## 🧭 Architecture

Flask serves the web interface and JSON API. The chatbot module validates answers and controls the conversation stages. The recommender loads the CSV, checks known criteria, calculates a relative match score, and explains each result.

```text
Visitor
  │
  ▼
Chat interface (HTML / CSS / JavaScript)
  │ JSON requests
  ▼
Flask API ─────── Chat flow and input validation
  │
  ├────────────── Rule-based recommendation engine
  │                       │
  └───────────────────────▼
                    Scheme catalogue (CSV)
```

## 📂 Project Structure

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

## 🚀 Installation on Windows

Open PowerShell in the project directory. Python 3.10 or newer is required.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell prevents environment activation, call the virtual environment directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

In VS Code, select `.venv\Scripts\python.exe` using **Python: Select Interpreter**.

## ▶️ Run Locally

```powershell
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). Stop the development server with `Ctrl+C`. The Flask debug server is for local development only and should not be exposed publicly.

## ☁️ Live Deployment

The project is deployed as a Flask web service on Render. GitHub hosts the source; GitHub Pages cannot run the Python backend.

- 🌐 **Live app:** [government-scheme-recommender.onrender.com](https://government-scheme-recommender.onrender.com/)
- 📦 **Source:** [github.com/prannoychandola/government-scheme-recommender](https://github.com/prannoychandola/government-scheme-recommender)
- 🆓 **Current instance:** Render Free

To deploy your own instance, create a Render **Web Service** from the public Git repository and configure:

| Setting | Value |
| --- | --- |
| Runtime | Python 3 |
| Branch | `main` |
| Build command | `pip install -r requirements.txt` |
| Start command | `gunicorn app:app` |
| Health check | `/` |

The included `render.yaml` can be used when creating a Render Blueprint. The currently published service was connected through Render's public Git repository option; manual redeployment may be required after future pushes. Free instances can spin down while idle, which may make the first request slower.

## 🔌 API

All API endpoints accept and return JSON except `GET /`, which serves the application page.

| Method and route | Purpose |
| --- | --- |
| `GET /` | Serve the chatbot interface |
| `GET /api/schemes` | List schemes; supports optional `category` and `q` query parameters |
| `POST /api/recommend` | Rank schemes using a supplied profile |
| `POST /api/chat` | Start or continue the guided conversation |
| `GET /api/scheme/<scheme_id>` | Retrieve one scheme's details; returns 404 if not found |

### `POST /api/recommend` example

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

The response contains `count` and `recommendations`. Invalid request shapes or profile values return HTTP 400. Each recommendation includes its relative score, reasons, eligibility status, and verification notes.

### `POST /api/chat` example

```json
{
  "message": "",
  "profile": {},
  "stage": "start"
}
```

Responses include the assistant's `reply`, the current `stage`, the `profile`, and question metadata when more input is needed. The completed conversation response also includes recommendations.

## 📊 Dataset

`data/government_schemes.csv` contains 100 catalogue entries with fields for scheme ID and name, department, category, description, eligibility, age, gender, income, state, education, occupation, benefits, application process, website, required documents, verification status, and source note.

This is a manually curated demonstration dataset, not an official or exhaustive live feed. Details that have not been independently confirmed are marked `Unknown - verify`; general directory links are not presented as validated scheme-specific sources. Some entries may be historical, umbrella programmes, or subject to changed rules. Confirm current details with the relevant official department before acting.

## 🧮 Recommendation Methodology

1. Validate and normalize the information supplied by the user.
2. Exclude a scheme only when a known eligibility rule explicitly conflicts with the profile.
3. Rank remaining candidates using interest relevance and known matching criteria.
4. Explain matching factors and list criteria that are missing or need verification.

Unknown rules are not assumed to be satisfied. The score is a relative rule-match ranking, not a probability, confidence value, or eligibility decision. The API returns at most 50 results.

## 🧪 Tests

Run the test suite from the project root:

```powershell
python -m unittest discover -s tests -v
```

Coverage includes catalogue integrity, explicit eligibility filtering, recommendation explanations, invalid chatbot input, numeric parsing, skip handling, the full conversation flow, API validation, and scheme details.

## 🖼️ Screenshots

Try the [live application](https://government-scheme-recommender.onrender.com/) to view the current interface. Screenshots can be added here as the project evolves.

## ⚠️ Limitations

- The catalogue is static, manually curated, incomplete, and not independently audited.
- Scheme eligibility, benefits, documents, availability, deadlines, and application steps can vary and change over time.
- Some entries may be umbrella, historical, or otherwise not currently open programmes.
- Text matching is literal and intentionally simple; it does not understand all synonyms or languages.
- This project does not use ML, NLP, an LLM, authentication, or persistent user storage.
- The free hosting tier can spin down when idle, and its terms may change.

## 🔮 Future Improvements

- Verify catalogue entries against dated official guidelines and source links.
- Add data freshness checks and a documented review/update workflow.
- Improve controlled vocabularies, language support, and matching coverage.
- Expand state-specific eligibility and accessibility testing.
- Add deployment monitoring and automated deployment through a connected repository Blueprint.

## 🔐 Privacy and Safety

The app does not request Aadhaar numbers, bank account information, passwords, or payment details. It does not persist conversation profiles. Avoid entering sensitive personal information, and use official government channels for applications and authoritative eligibility guidance.