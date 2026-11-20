# FoodMatch

FoodMatch helps one person or a group find a restaurant. Choose a location and preferences, swipe through a shortlist, then open a favourite or group match in Google Maps. Guests join a group through an invite link and pick a display name.

The React 19 and Vite frontend uses TypeScript, Tailwind, Motion, React Router, Axios, and Lucide. FastAPI owns guest sessions, restaurant discovery, and voting. SQLAlchemy and Alembic manage PostgreSQL. WebSockets notify browsers when to reload room state from the REST API.

## Run locally

Install Python 3.12 or newer, Node 22, and Docker with Compose. From the repository root, start PostgreSQL.

```sh
docker compose up -d --wait db
```

In a backend terminal, run the following from the repository root.

```sh
cd backend
cp .env.example .env
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

In a second terminal, run the frontend.

```sh
cd frontend
cp .env.example .env
npm ci
npm run dev
```

Open [FoodMatch](http://localhost:5173), [API documentation](http://localhost:8000/docs), or [API health](http://localhost:8000/api/health). Start with `RESTAURANT_PROVIDER=mock`. The 36 fictional venues use sample coordinates and illustrative food photos, so a sample map pin represents a test location. Select any supported city or use custom coordinates to try the flows.

For separate local guests on one computer, open the invite in separate browser profiles or private sessions. Browsers that share a profile also share the room’s guest token. For phones on the same Wi-Fi, open the frontend at `http://<developer-machine-LAN-IP>:5173`, set `VITE_API_URL` to `http://<developer-machine-LAN-IP>:8000`, and add the exact LAN frontend origin to `CORS_ORIGINS`. Restart both servers after editing environment variables. The default city selector works over LAN HTTP. Browser geolocation and clipboard access use HTTPS or localhost, and invite copying has a selectable-text fallback.

## Configuration

| Service | Variable | Purpose |
| --- | --- | --- |
| Backend | `DATABASE_URL` | PostgreSQL connection string. The examples point to Compose. |
| Backend | `CORS_ORIGINS` | JSON array of allowed frontend origins, including scheme and port. This also controls browser WebSocket origins. |
| Backend | `RESTAURANT_PROVIDER` | `mock` for local data or `google` for live Places data. |
| Backend | `GOOGLE_PLACES_API_KEY` | Server-only key for Places API (New). |
| Backend | `ROOM_TTL_HOURS` | Room and guest-access lifetime from creation. Defaults to 24 hours. |
| Backend | `RATE_LIMIT_CLIENT_IP_HEADER` | Optional trusted ingress header. Use `x-real-ip` behind Railway and leave blank locally. |
| Frontend | `VITE_API_URL` | Public FastAPI origin. The browser derives the WebSocket scheme from it. |

The backend loads `backend/.env` when started from that directory. Copy the frontend and backend examples separately. Vite bakes its public API origin into the build.

### Live restaurant discovery

Enable Places API (New) and billing for a Google Cloud project. Set `RESTAURANT_PROVIDER=google` and `GOOGLE_PLACES_API_KEY` in the backend environment. Restrict the key to Places API (New). Set Google Cloud quotas to match your expected traffic.

The provider uses Nearby Search, Place Details, and Place Photos with explicit field masks and retries delegated to the user. PostgreSQL keeps the Google place IDs that define the room deck. Google names, photos, photo references, locations, and prices are loaded for display or matching as needed. API responses use `Cache-Control: no-store`. Photo requests use the backend key and return a media redirect with attribution rendered alongside the image. The frontend stores IDs and votes for solo resume. Live venue details stay in memory during the current visit.

Live cuisines come from supported Google place types. The provider can identify broad categories such as Indian, Italian, and Chinese. The preference form shows the categories supported by the active provider. Regional categories such as South Indian and Biryani are available in the mock catalog. Vegetarian-only screens require the vegetarian or vegan restaurant type. Missing ratings, prices, and cuisines display as unavailable. The budget filter excludes known INR price ranges outside the requested budget and retains listings with no INR price. The app shows Google’s price range as supplied. The mock deck displays a two-person estimate. [Google Places field reference](https://developers.google.com/maps/documentation/places/web-service/data-fields) · [Places attribution and data policies](https://developers.google.com/maps/documentation/places/web-service/policies) · [Place Photos](https://developers.google.com/maps/documentation/places/web-service/place-photos)

## Rooms and matching

The host creates a room, shares the invite through WhatsApp or copies it, and starts a round from the lobby. Up to 30 guests can use a room, including the host. Each browser keeps a room-scoped bearer token. The database stores only its SHA-256 digest. Display names must be unique within a room, ignoring case.

The room stores a fixed pool of up to ten candidates per round. PostgreSQL serializes room mutations with a row lock. A unique vote constraint prevents duplicate ballots, and an exact retry returns the existing state. The API checks the round number so an old request cannot change a new round. Participants see progress counts and completion status during voting.

The round ends after every participant still enrolled completes the deck or the host closes voting. Temporary disconnection preserves the guest’s enrollment and votes. An away guest can return with their token. A guest who explicitly leaves is removed from the round, and a host with missing voters can finish early. A disconnected host keeps their role and can resume from the original browser. Rooms and tokens stop working at expiration.

The matcher ranks restaurants with at least one like by group support, then by approval among votes cast, budget compatibility, distance, and stable restaurant ID. A unanimous result requires a like from every enrolled participant. Results show the fraction of the group that liked each place and, when some votes are missing, the approval rate among submitted ballots. Missing votes lower the possible share of support without becoming dislikes. A new round keeps the same invite and preferences, prioritizes unused candidates, and replaces the previous round’s votes and results.

The browser authenticates to `/ws/rooms/{code}` in its first message. Events report participant joins and departures, room transitions, progress, completion, and results readiness without disclosing private ballots. The browser retries WebSocket connections with backoff and polls REST state while reconnecting. Run one worker and one backend replica for the MVP. Scaling to multiple replicas requires shared event fanout, presence, and rate limiting.

## Tests and migrations

From `backend`, with the virtual environment activated:

```sh
python -m pytest
alembic current
alembic check
FOODMATCH_TEST_DATABASE_URL=postgresql+psycopg://foodmatch:foodmatch@127.0.0.1:5432/foodmatch python -m pytest
```

Tests use temporary SQLite databases by default. Set `FOODMATCH_TEST_DATABASE_URL` to run the same suite plus the concurrency test in temporary PostgreSQL schemas. Use a disposable local database with schema creation rights. To regenerate migration SQL for review, run `alembic upgrade head --sql`.

From `frontend`:

```sh
npm test
npm run build
```

The frontend tests cover room creation, loading and invite joining, voting controls, and results. To verify realtime behavior end to end, open the same invite in four isolated browser profiles, refresh one profile mid-round, and check progress and results from all four.

## Deploy

1. **Supabase** — Create a project and obtain a PostgreSQL connection string from the Connect panel. Use the direct connection when the backend has IPv6 access or the session pooler on port 5432 for IPv4. Add `sslmode=require`. Supply a database role that owns the FoodMatch tables so migrations can manage them and the backend can query them. The migrations enable row-level security with no public policies for the FoodMatch tables. [Supabase connection documentation](https://supabase.com/docs/guides/database/connecting-to-postgres)
2. **Railway** — Connect the repository, set the service root to `/backend`, and build with the included Dockerfile. Set the backend environment variables, including `RATE_LIMIT_CLIENT_IP_HEADER=x-real-ip` for requests through Railway’s public ingress. Configure `alembic upgrade head` as the pre-deploy command and `/api/health` as the health check path, then generate an HTTPS domain. The Dockerfile starts a single Uvicorn worker on Railway’s `PORT`. [Railway pre-deploy commands](https://docs.railway.com/deployments/pre-deploy-command) · [Railway request headers](https://docs.railway.com/networking/public-networking/specs-and-limits#request-headers)
3. **Vercel** — Import the repository, select `frontend` as the root, and use the Vite preset with Node 22. Set `VITE_API_URL` to the Railway HTTPS origin before building. The included rewrites support opening room invites directly. Add the production Vercel origin and any intended custom frontend origins to Railway’s `CORS_ORIGINS`, then redeploy the backend. [Vite on Vercel](https://vercel.com/docs/frameworks/frontend/vite)
4. **Smoke test** — Check `/api/health`, open a production invite URL on a phone, and run one mock round before enabling live discovery. The frontend includes public privacy and terms pages with Google links for a live deployment.

## Photography

Mock dish photographs come from Unsplash and illustrate types of food served. [Indian dish](https://images.unsplash.com/photo-1631452180519-c014fe946bc7) · [Masala dosa by Zoshua Colah](https://unsplash.com/photos/a-delicious-dosa-is-served-with-sides-3qHDm3IQCUs) · [Biryani](https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8) · [Pasta](https://images.unsplash.com/photo-1551183053-bf91a1d81141) · [Pizza](https://images.unsplash.com/photo-1574071318508-1cdbab80d002) · [Café](https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb) · [Noodles](https://images.unsplash.com/photo-1569718212165-3a8278d5f624)
