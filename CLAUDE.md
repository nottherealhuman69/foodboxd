# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repo Structure

```
foodboxd/
  backend/        # FastAPI app — single file: main.py
  frontend/       # React + Vite SPA
  .venv/          # Python virtualenv (ignore)
```

## Commands

**Backend** (run from repo root or `backend/`):
```bash
# activate venv first (Windows)
.venv\Scripts\activate

uvicorn backend.main:app --reload        # dev server on :8000
```

**Frontend** (run from `frontend/`):
```bash
npm install
npm run dev      # Vite dev server on :5173
npm run lint     # oxlint
npm run build
```

## Architecture

### Backend (`backend/main.py`)
Single-file FastAPI app. No routers — all endpoints are defined inline in `main.py`. `create_tables()` runs on startup and is the source of truth for the DB schema.

- **Auth**: JWT tokens (HS256, 24h expiry) via `Authorization: Bearer <token>`. `get_current_user` dependency extracts `email` from the token and passes it as a string to every protected endpoint.
- **DB**: Raw `psycopg2` with `RealDictCursor` (rows as dicts). No ORM. `get_db` yields a connection per request. `DATABASE_URL` and `SECRET_KEY` are loaded from `backend/.env`.
- **Tables**: `users`, `dish_reviews`, `friendships`, `trylists`
- **Username convention**: There are no separate usernames — the email prefix (`email.split("@")[0]`) is used as the display username everywhere.

### Frontend (`frontend/src/`)
React 19 SPA with React Router v7. Auth token stored in `localStorage` under key `token`. `PrivateRoute` in `App.jsx` gates all protected pages.

- **Pages**: `Dashboard`, `Search`, `Feed`, `Profile`, `Userprofile`, `Reviews`, `Createreview`, `Dishpage`, `Restaurantpage`, `Trylist`, `Notifications`, `Login`, `Signup`
- **No state management library** — component-local state via `useState`/`useEffect`, API calls via `fetch` with `Authorization: Bearer ${localStorage.getItem('token')}` header
- **API base**: `http://localhost:8000` (hardcoded in each page component)

### Key data model notes
- `dish_reviews.type` is `'restaurant'` or `'homemade'`. Dish/restaurant pages only aggregate `type = 'restaurant'` rows.
- `friendships` is directional (`requester_email` → `addressee_email`). Both directions are checked in queries. Status: `pending` → `accepted` or `declined`.
- `trylists` supports `item_type = 'dish'` (requires both `dish_name` and `restaurant_name`) or `'restaurant'` (requires only `restaurant_name`).
- The `/trylist/check` route must be declared **before** `/trylist/{item_id}` in `main.py` to avoid FastAPI treating `"check"` as an integer path param.
