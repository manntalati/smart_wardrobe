# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Commands

### Backend
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
npm run build      # production build
npm run lint       # ESLint
```

### Database
- SQLite DB auto-created at `backend/wardrobe.db` on first run via `init_db()`
- Schema changes go through Alembic (always `cd backend` first):
  - **Existing DB**: `alembic stamp head` then `alembic upgrade head`
  - **Fresh install**: `alembic upgrade head` (tables created by `init_db()` on startup, which is idempotent)
  - **New migration**: `alembic revision --autogenerate -m "description"` then edit + `alembic upgrade head`

---

## Environment Variables

**`backend/.env`**:
```
GEMINI_API_KEY=...          # Google AI Studio — falls back to rule-based if absent
OPENWEATHER_API_KEY=...     # OpenWeatherMap — skips weather context if absent
GOOGLE_CLIENT_ID=...        # Google OAuth app ID
GOOGLE_CLIENT_SECRET=...    # Google OAuth app secret
SECRET_KEY=...              # JWT signing key
```

**`frontend/.env.local`**:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_GOOGLE_CLIENT_ID=...
```

**Dev bypass**: If `GOOGLE_CLIENT_ID` is unset or the token is `"test-token"`, backend returns a mock user — no OAuth setup needed locally.

---

## Current Architecture

### Backend (`backend/`)

**`main.py`** — App setup, middleware, router registration, startup FAISS init, `/api/v1/health`

**`config.py`** — `BASE_DIR`, `UPLOAD_DIR`, `THUMBNAIL_DIR` path constants (import from here, not re-derive)

**`schemas.py`** — `ok(data, meta)` helper; all endpoints return `{ data, error, meta }` envelope

**`routers/`** — one file per domain; all paths under `/api/v1/`:
- `auth.py` — `POST /auth/login`
- `items.py` — full CRUD + `/from-url` + `/{id}/similar` + `PATCH /{id}` (edit)
- `recommendations.py` — `GET /recommendations`
- `shopping.py` — `GET /shopping`
- `search.py` — `GET /search` (DuckDuckGo)

**`models/`**:
- `database.py` — `ClothingItem`: category, color, pattern, season, fabric, occasion_tags (JSON), CLIP embedding (JSON), confidence, image_path, **notes**, user_id FK; `to_dict()` derives `thumbnail_path` by convention
- `user.py` — `User`: email, google_id, full_name, avatar_url

**`services/`**:
- `classifier.py` — CLIP `openai/clip-vit-base-patch32` zero-shot across 5 dims + occasion tags; 512-D embeddings; lazy-loaded on first call
- `embeddings.py` — `EmbeddingIndex` wrapping FAISS `IndexFlatIP`; persisted to `faiss_index.bin`; `user_map` per-user isolation; auto-reconcile on startup with structured logging
- `image_optimizer.py` — resize to 800px (display) + 256px (thumbnail), strip EXIF, save as JPEG; called before CLIP inference
- `recommender.py` — Gemini 2.0 Flash outfit generation; rule-based fallback
- `rag.py` — Chunks `knowledge/fashion_guide.md`, CLIP text embeddings, cosine-similarity retrieval
- `weather.py` — OpenWeatherMap → temperature, conditions, style hints
- `shopping.py` — Wardrobe gap analysis + Gemini suggestions
- `auth.py` — Google ID token → JWT (30-day, HS256); `get_current_user()` FastAPI dependency
- `search.py` — DuckDuckGo image search + URL download

**`alembic/`** — Alembic migration history. Run from `backend/` dir.

### Frontend (`frontend/src/`)

**`lib/auth.tsx`** — `AuthContext`; JWT in cookies, user in localStorage; auto-redirect to `/login`

**`lib/api.ts`** — Typed fetch wrapper; `ApiResponse<T>` envelope type; all URLs at `/api/v1/`; attaches `Authorization: Bearer` from cookie

**Pages**: `/` (dashboard), `/login` (Google OAuth), `/wardrobe` (upload + search + edit + pagination), `/outfits` (recommendations), `/shopping` (gap analysis)

### Data Flows

**Upload**: image → CLIP classify (5 dims + occasion tags) → CLIP embed → FAISS + SQLite

**Recommendations**: weather fetch → wardrobe query → RAG retrieval (fashion_guide.md) → Gemini prompt → structured outfits

**Similarity**: item embedding → FAISS `IndexFlatIP` search → filter by `user_id`

---

## Architecture Plan: Going Forward

The goal is to evolve this from a working prototype into a clean, extensible product. The plan is organized into phases — each phase must be complete and stable before moving to the next.

---

### Phase 1 — Foundation Hardening ✅ COMPLETE

**1.1 Alembic migrations** — `migrate_db.py` replaced; all schema changes go through `alembic/versions/`

**1.2 Route decomposition + response envelope** — `main.py` slimmed to app setup; all routes in `routers/`; all endpoints return `{ data, error, meta }`; all paths under `/api/v1/`

**1.3 Image optimization** — `services/image_optimizer.py`; resize + EXIF strip + JPEG conversion before CLIP inference; thumbnails stored in `uploads/thumbnails/`

**1.4 FAISS stability** — startup reconciliation with structured `logging`; save error handling; FAISS initialized eagerly on startup

**1.5 Pagination** — `GET /api/v1/items?page=&limit=`; `meta: { total, page, limit }` in response; frontend has Load More button

**1.6 Item editing** — `PATCH /api/v1/items/{id}` for name, season, occasion_tags, notes; edit modal in wardrobe page

---

### Phase 2 — Core Product Features

**2.1 Outfit Persistence**
The biggest missing feature: recommendations currently vanish on page reload.

New DB model: `Outfit`
- `id`, `user_id`, `name`, `description`, `item_ids` (JSON array), `occasion`, `style_notes`, `is_favorite`, `created_at`

New endpoints:
- `POST /api/v1/outfits` — save a generated outfit
- `GET /api/v1/outfits` — list saved outfits
- `PATCH /api/v1/outfits/{id}` — rename, favorite, update notes
- `DELETE /api/v1/outfits/{id}`

Frontend: add save button on each outfit card; new `/outfits/saved` tab showing persisted outfits.

**2.2 Wear Tracking**
New fields on `ClothingItem`: `wear_count` (int, default 0), `last_worn_at` (datetime)

New endpoint: `POST /api/v1/items/{id}/wear` — increments count, sets timestamp

Frontend: "Worn Today" button on item cards in wardrobe view. Show wear count and last worn date on item detail.

This data unlocks future features: surface unworn items, cost-per-wear calculation, rotation suggestions.

**2.3 Style Profile**
New DB model: `UserProfile`
- `user_id` (FK, 1:1), `style_preferences` (JSON — e.g., ["minimalist", "classic"]), `body_type`, `budget_range`, `avoided_colors` (JSON), `preferred_brands` (JSON), `notes`

New endpoints:
- `GET /api/v1/profile`
- `PUT /api/v1/profile`

Feed `style_preferences` and `avoided_colors` directly into the Gemini recommendation prompt — currently the style hint is a one-time request param; the profile makes it persistent.

**2.4 Advanced Wardrobe Filtering**
Current filters: category, color (client-side only)

Add server-side filtering to `GET /api/v1/items`:
- `?season=`, `?occasion=`, `?pattern=`, `?fabric=`
- `?worn_before=YYYY-MM-DD` (items not worn since a date — surface forgotten items)
- `?sort=wear_count|last_worn|created_at`

Frontend: filter sidebar on `/wardrobe` page.

---

### Phase 3 — Intelligence Layer

**3.1 Outfit Calendar**
New DB model: `OutfitPlan`
- `user_id`, `outfit_id` (FK nullable — plan can reference saved outfit or be freeform), `planned_date`, `notes`, `weather_snapshot` (JSON)

New endpoints:
- `GET /api/v1/calendar?from=&to=` — returns planned outfits for date range
- `POST /api/v1/calendar` — plan an outfit for a date
- `DELETE /api/v1/calendar/{id}`

Frontend: `/calendar` page with weekly view; drag-drop outfit cards onto days; weather forecast per day (extend weather service to support forecast, not just current).

**3.2 Wardrobe Analytics**
New endpoint: `GET /api/v1/analytics`

Returns:
- Cost-per-wear per item (requires price field on `ClothingItem`)
- Category distribution over time
- Most/least worn items
- Color palette visualization data
- "Dead stock" items (added >90 days ago, never worn)
- Seasonal coverage score

Frontend: `/analytics` page with charts. Use a lightweight charting lib (recharts already available via Lucide ecosystem or add `recharts`).

**3.3 Personalized RAG**
Currently `rag.py` only reads from the static `fashion_guide.md`.

Extend to also retrieve from:
- User's own outfit history (saved outfits + wear occasions become implicit knowledge)
- User's style profile preferences
- Items they frequently wear together (derived from `Outfit.item_ids` co-occurrence)

This makes recommendations genuinely personalized over time without extra user effort.

**3.4 Capsule Wardrobe Wizard**
A guided multi-step flow that analyzes the current wardrobe and produces a target capsule plan:
1. User selects their lifestyle (professional, casual, mixed)
2. System analyzes current wardrobe coverage
3. Gemini generates a 30-40 piece target capsule (what to keep, what to add, what to remove)
4. Output: actionable list with priorities

New endpoint: `POST /api/v1/capsule` — takes lifestyle param, returns capsule plan

**3.5 Packing List Generator**
New endpoint: `POST /api/v1/packing-list`

Input: `{ destination, days, occasions: [], weather_forecast }`
Output: curated list of items from user's wardrobe (pulled by FAISS similarity to occasion + weather context) + gaps to buy

---

### Phase 4 — Production Readiness

**4.1 Background Job Processing**
CLIP classification currently blocks the HTTP request (can take 10–30s on first run).

Add `celery` + `redis` (or use FastAPI's `BackgroundTasks` as a lighter alternative):
- Upload endpoint returns immediately with `{ item_id, status: "processing" }`
- Classification runs async
- `GET /api/v1/items/{id}` returns `status: "ready" | "processing"`
- Frontend polls or uses SSE to get notified when classification completes

**4.2 Caching Layer**
Add Redis (or `cachetools` in-process for simpler start):
- Weather responses: cache per city for 30 minutes
- RAG chunks + embeddings: cache in memory at startup instead of re-embedding on every request
- CLIP model: keep warm (currently lazy-loaded; add explicit warmup on startup)

**4.3 PostgreSQL + Connection Pooling**
When multi-user scale requires it:
- Alembic (added in Phase 1) makes this a config change
- Replace `sqlite:///wardrobe.db` with `postgresql+asyncpg://...`
- Add `asyncpg` driver, use async SQLAlchemy session

**4.4 Rate Limiting + Security**
- Add `slowapi` rate limiting on upload and recommendation endpoints
- Add request size limits on image upload (currently unconstrained)
- Validate image MIME type server-side (not just extension)

**4.5 Docker Compose**
```
services:
  backend:   FastAPI + uvicorn
  frontend:  Next.js
  redis:     for caching (Phase 4.2+)
```
Add `Dockerfile` for each service, `docker-compose.yml` at root.

---

## New Models Summary (post-Phase 1)

| Model | Phase | Purpose |
|---|---|---|
| `Outfit` | 2.1 | Saved outfit collections |
| `UserProfile` | 2.3 | Persistent style preferences |
| `OutfitPlan` | 3.1 | Calendar scheduling |
| Add `wear_count`, `last_worn_at`, `price`, `notes` to `ClothingItem` | 2.2 | Wear tracking + analytics |

---

## New API Endpoints Summary

| Endpoint | Phase | Method |
|---|---|---|
| `PATCH /api/v1/items/{id}` | 1.6 | Edit item metadata |
| `POST /api/v1/items/{id}/wear` | 2.2 | Log wear event |
| `GET/POST/PATCH/DELETE /api/v1/outfits` | 2.1 | Outfit persistence |
| `GET/PUT /api/v1/profile` | 2.3 | Style profile |
| `GET /api/v1/analytics` | 3.2 | Wardrobe analytics |
| `POST /api/v1/capsule` | 3.4 | Capsule wardrobe plan |
| `POST /api/v1/packing-list` | 3.5 | Travel packing |
| `GET /api/v1/calendar` + `POST/DELETE` | 3.1 | Outfit calendar |

---

## Coding Conventions

- **Backend**: Add new features as new service files in `services/`; add new route groups as files in `routers/`; never add routes directly to `main.py` beyond registration
- **Frontend**: New pages get their own directory under `app/`; shared UI components go in `components/`; API calls go through `lib/api.ts` only — never `fetch()` directly in components
- **DB changes**: Always go through Alembic migration (Phase 1+); never ALTER TABLE manually
- **ML services**: Keep CLIP and Gemini calls isolated in their respective service files; callers should not import `transformers` or `google.generativeai` directly
