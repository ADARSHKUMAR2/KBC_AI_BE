# Task & To-Do Tracker

## Phase 1: Foundation & Authentication

### ✅ Completed Tasks (Backend)
- [x] Initialized Python environment using `uv`.
- [x] Scaffolded Microservice Folder Structure (Auth, Game, Gateway, Shared).
- [x] Set up MVC architecture inside services (config, controllers, routes, models).
- [x] Configured MongoDB Atlas credentials in `backend/.env`.
- [x] Created `shared/database.py` for global MongoDB connection using Motor/Beanie.
- [x] Fixed port binding bugs (string to int) for Uvicorn.
- [x] Added internal Uvicorn run blocks to `main.py` files for easy execution.
- [x] Created base Beanie `User` model in the Auth service.
- [x] Documented Project Phases and To-Do lists.

### ⏳ Pending Tasks: Phase 1 (Auth & Gateway)
- [ ] **Shared:** Write `shared/auth_utils.py` (password hashing with `passlib`, JWT generation/decoding).
- [ ] **Auth Controllers:** Write `auth_controller.py` to handle user registration logic and duplicate email checks.
- [ ] **Auth Routes:** Write `auth_routes.py` and attach to FastAPI app in `auth/main.py`.
- [ ] **Gateway Middlewares:** Write `gateway/middlewares/auth_middleware.py` to intercept and validate JWT tokens from Unity.
- [ ] **Gateway Proxy:** Write `gateway/controllers/proxy_controller.py` using `httpx` to forward Unity's requests to `localhost:8001` (Auth) and `localhost:8002` (Game).
- [ ] **Gateway Routes:** Write `gateway/routes/proxy_routes.py` and attach to FastAPI app in `gateway/main.py`.

### ⏳ Pending Tasks: Phase 2 & 3 (Gameplay & Traitors)
- [ ] **Game Models:** Create `Question`, `Expert`, and `GameSession` Beanie models.
- [ ] **Game Logic:** Implement session generation (picking questions, assigning personalities).
- [ ] **Traitor System:** Add random assignment of the "Saboteur" role per session.
- [ ] **Economy System:** Write endpoints to update User coins upon winning/losing.

### ⏳ Pending Tasks: Phase 3.5 (Redis & Optimization)
- [ ] **Redis Setup:** Create `shared/redis.py` connection manager using `aioredis`.
- [ ] **Game Session Cache:** Cache active sessions in Redis (key: `game_session:{id}`, TTL: 30 min).
- [ ] **Rate Limiting:** Add rate limiting middleware in Gateway (100 req/min per Firebase UID).
- [ ] **Leaderboard:** Implement Redis sorted set for top 100 players by score.
- [ ] **Monitoring:** Add Redis health check endpoint (`/health/redis`).

### ⏳ Pending Tasks: Phase 4 (LLM Integration)
- [ ] **LLM Logic:** Integrate LangChain/Groq for dynamic responses.
- [ ] **Prompt Engineering:** Create specific personality prompts (Historian, Risky, Saboteur).
- [ ] **Streaming:** Stream responses to Gateway -> Unity.

### ⏳ Pending Tasks: Unity (Frontend)
- [ ] **Setup:** Create new 2D project, setup scene structure.
- [ ] **UI:** Build Login/Register Canvas.
- [ ] **Networking:** Create `AuthClient.cs` to hit API Gateway endpoints.
- [ ] **UI:** Build Gameplay Canvas (Question text, 4 buttons, 3 Expert panels).
- [ ] **Networking:** Create `GameClient.cs` to fetch questions and expert opinions.
- [ ] **UI/UX:** Add post-game summary (Traitors revealed, Coins earned).
- [ ] **Networking:** Implement streaming text handler for LLM responses.