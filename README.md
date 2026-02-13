# 🧠 Smart Wardrobe — AI-Powered Style Assistant

An intelligent wardrobe assistant that lets you photograph/upload clothing items, catalogs them with CLIP-based classification, and delivers outfit recommendations using weather data, occasion context, and Google Gemini AI.

## Features

- **📸 Image Upload & AI Classification** — Upload clothing photos; CLIP classifies category, color, pattern, season, fabric, and occasion automatically
- **✨ Outfit Recommendations** — Gemini AI generates outfit suggestions based on your wardrobe, weather, occasion, and style preferences  
- **🌤️ Weather Integration** — OpenWeatherMap provides real-time weather context for weather-appropriate outfits
- **🛍️ Shopping Suggestions** — Gap analysis identifies what's missing from your wardrobe and recommends purchases
- **🔍 Similarity Search** — FAISS vector index finds visually similar items in your wardrobe

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 (App Router), TypeScript |
| Backend | Python, FastAPI, Uvicorn |
| Database | SQLite, SQLAlchemy |
| ML Model | CLIP (`openai/clip-vit-base-patch32`) via HuggingFace |
| Vector Search | FAISS |
| LLM | Google Gemini 1.5 Flash |
| Weather | OpenWeatherMap API (free tier) |
| RAG | CLIP text embeddings + fashion knowledge base |

## Quick Start

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY and OPENWEATHER_API_KEY

# Start the backend
uvicorn main:app --reload --port 8000
```

> **Note:** The CLIP model (~600MB) will download on first run. First classification may take 10-30 seconds.

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## API Keys

| Key | Required | Free? | Get it at |
|-----|----------|-------|-----------|
| `GEMINI_API_KEY` | Optional (enables AI recommendations) | Yes, free tier | [Google AI Studio](https://aistudio.google.com/) |
| `OPENWEATHER_API_KEY` | Optional (enables weather) | Yes, free tier (60 calls/min) | [OpenWeatherMap](https://openweathermap.org/api) |

The app works without API keys — you'll get rule-based outfit suggestions instead of AI-powered ones, and no weather data.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/items` | Upload & classify a clothing image |
| `GET` | `/api/items` | List all wardrobe items |
| `GET` | `/api/items/{id}` | Get a single item |
| `DELETE` | `/api/items/{id}` | Remove an item |
| `GET` | `/api/items/{id}/similar` | Find similar items |
| `GET` | `/api/recommendations` | Get outfit recommendations |
| `GET` | `/api/shopping` | Get shopping suggestions |
| `GET` | `/api/health` | Health check |

## Project Structure

```
smart_wardrobe/
├── backend/
│   ├── main.py                  # FastAPI app + API routes
│   ├── requirements.txt
│   ├── .env.example
│   ├── models/
│   │   └── database.py          # SQLAlchemy models
│   ├── services/
│   │   ├── classifier.py        # CLIP zero-shot classification
│   │   ├── embeddings.py        # FAISS vector index
│   │   ├── weather.py           # OpenWeatherMap integration
│   │   ├── recommender.py       # Outfit recommendation engine
│   │   ├── shopping.py          # Shopping gap analysis
│   │   └── rag.py               # Fashion RAG pipeline
│   └── knowledge/
│       └── fashion_guide.md     # Fashion knowledge base
└── frontend/
    ├── src/
    │   ├── app/
    │   │   ├── page.tsx         # Dashboard
    │   │   ├── wardrobe/page.tsx # Wardrobe catalog + upload
    │   │   ├── outfits/page.tsx  # Outfit recommendations
    │   │   └── shopping/page.tsx # Shopping suggestions
    │   └── lib/
    │       └── api.ts           # API client
    └── package.json
```