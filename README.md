# Trailbit

**Trailbit** is an open-source contribution discovery and onboarding platform that helps beginner developers find their first open-source contributions.

## Features
- Live discovery of GitHub issues using TinyFish API
- Verification of issue status, PRs, and activity
- Automated generation of a beginner‑friendly contribution roadmap
- Simple, dark‑themed UI with responsive design

## Tech Stack
- **Frontend**: HTML5, CSS3, JavaScript (no framework for MVP)
- **Backend**: Python 3.11, FastAPI, Uvicorn, Pydantic
- **Live research**: TinyFish Web API

## Architecture
```
trailbit/
├─ backend/
│  ├─ main.py
│  ├─ routes/
│  │  ├─ discover.py
│  │  ├─ verify.py
│  │  └─ contribution_plan.py
│  ├─ models/
│  │  ├─ request.py
│  │  └─ response.py
│  ├─ services/
│  │  └─ tinyfish.py
│  └─ utils.py
├─ frontend/
│  ├─ index.html
│  ├─ style.css
│  └─ app.js
├─ .env.example
├─ .gitignore
└─ README.md (this file)
```