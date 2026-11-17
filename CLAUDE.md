# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repo Structure

```
foodboxd/
  backend/        # FastAPI app — package in backend/app/, entry point backend/main.py
                  # migrations/ + alembic.ini: database schema (Alembic)
  frontend/       # React + Vite SPA
```

## Commands

**Backend** (Python env: the conda env `foodboxd`; run from `backend/`, so the `app` package is importable):
```bash
conda activate foodboxd
cd backend
uvicorn main:app --reload        # dev server on :8000 (same as uvicorn app.main:app)
```

**Database migrations** (Alembic, run from `backend/`):
```bash
alembic upgrade head                    # apply new migrations to DATABASE_URL (the real DB)
alembic -x db=test upgrade head         # same, against TEST_DATABASE_URL (local test DB)
alembic current                         # which migration a database is on
alembic revision -m "add x" --rev-id 0003   # new migration file in migrations/versions/
```
**Tests** (pytest, run from `backend/`; needs `TEST_DATABASE_URL` in `backend/.env` pointing at a local Postgres):
```bash
pip install -r requirements-dev.txt     # once
pytest                                  # whole suite
pytest tests/test_reviews.py -k likes   # one file / matching tests
```
`tests/conftest.py` refuses any non-localhost test DB, rebuilds the schema with the migrations, and empties every table before each test. Use the `client`, `make_user` / `alice` / `bob` / `carol` fixtures and `tests/helpers.py` (`follow`, `review`, `meal`, ...). Bugs found but not yet fixed live in `tests/test_known_issues.py` as `xfail(strict=True)` tests; when you fix one, delete its marker.

The app does **not** create or change tables at startup. Every schema change is a new migration file (raw SQL via `op.execute`, with a `downgrade()`); never edit a migration that has already been applied to the real database.

**Frontend** (run from `frontend/`):
```bash
npm install
npm run dev      # Vite dev server on :5173
npm run lint     # oxlint
npm run build
```

## Architecture

### Backend (`backend/app/`)
FastAPI app split into layers. `backend/main.py` is only a shim that re-exports `app.main:app`.

```
app/
  main.py          # creates the FastAPI app, CORS, includes every router
  core/            # config.py (env settings), db.py (get_db), security.py (hashing, JWT, get_current_user)
  routers/         # one APIRouter per area: auth, reviews, meals, posts, users, social, feed,
                   # places, trylist, lists, group_lists, notifications
  schemas/         # Pydantic request/response models, grouped the same way
  services/        # shared business logic used by several routers (posts, group_lists, social,
                   # recipes, meals, lists, email, validation)
  utils.py         # serialisers (serialise_review / serialise_meal) and username_from
```

- New endpoints go in the matching `routers/` file; logic used by more than one router goes in `services/`. Routers are included in `app/main.py`.
- **Config**: `SECRET_KEY` and `DATABASE_URL` are required (no fallbacks; the app refuses to start without them). Optional: `CORS_ORIGINS` (comma-separated), `FRONTEND_URL`, `SMTP_*`.

- **Auth**: JWT tokens (HS256, 24h expiry) via `Authorization: Bearer <token>`. `get_current_user` dependency extracts `email` from the token and passes it as a string to every protected endpoint.
- **DB**: Raw `psycopg2` with `RealDictCursor` (rows as dicts). No ORM. `get_db` yields a connection per request. `DATABASE_URL` and `SECRET_KEY` are loaded from `backend/.env`.
- **Schema**: defined by the migrations in `backend/migrations/versions/` (source of truth). `0001_baseline` is the schema as it existed in the real database; `0002` removes unused leftovers.
- **Tables**: `users`, `dish_reviews`, `recipe_ingredients`, `meals`, `meal_likes`, `meal_comments`, `meal_comment_likes`, `review_likes`, `review_comments`, `review_comment_likes`, `friendships`, `trylists`, `custom_lists`, `list_items`, `group_lists`, `group_list_members`, `group_list_items`, `post_tags`, `post_reposts`
- **Username convention**: There are no separate usernames — the email prefix (`email.split("@")[0]`) is used as the display username everywhere.

### Frontend (`frontend/src/`)
React 19 SPA with React Router v7. `PrivateRoute` in `App.jsx` gates all protected pages.

- **Pages**: `Dashboard`, `Search`, `Feed`, `Profile`, `Userprofile`, `Reviews`, `Createreview`, `Dishpage`, `Restaurantpage`, `Trylist`, `Notifications`, `Login`, `Signup`
- **No state management library** — component-local state via `useState`/`useEffect`.
- **API layer (`src/api/`)**: all backend calls go through it — never call `fetch` directly from a page. One file per backend router with one function per endpoint (74, matching `backend/app/routers/`). Use `import * as api from '../api'`, then e.g. `api.reviews.toggleLike(id)`. Functions return the raw fetch `Response` (callers check `res.ok` / `res.json()`); request bodies are passed as plain objects.
  - `client.js`: base URL (`VITE_API_URL`, default `/api`), auth header, JSON encoding, and on a 401 for a request that carried a token, clears the session and redirects to `/login`.
  - `session.js`: the only place that reads/writes the token and email (`localStorage` keys `token`, `email`). Use `api.session.getEmail()` etc.
  - `api.posts.forKind('review' | 'meal')` returns the reviews or meals module (same function names) for code that handles both.
  - `useFetch(api.x.y)` in `hooks/useApi.js` takes an api function, not a URL.
- **API base**: in dev, `/api/...` is proxied to `http://localhost:8000` by the Vite dev server (`vite.config.js` strips the `/api` prefix). Set `VITE_API_URL` to call a backend directly.

### Key data model notes
- `dish_reviews.type` is `'restaurant'` or `'homemade'`. Dish/restaurant pages only aggregate `type = 'restaurant'` rows.
- `friendships` is directional (`requester_email` → `addressee_email`). Both directions are checked in queries. Status: `pending` → `accepted` or `declined`.
- `trylists` supports `item_type = 'dish'` (requires both `dish_name` and `restaurant_name`) or `'restaurant'` (requires only `restaurant_name`).
- The `/trylist/check` route must be declared **before** `/trylist/{item_id}` in `app/routers/trylist.py` to avoid FastAPI treating `"check"` as an integer path param.
