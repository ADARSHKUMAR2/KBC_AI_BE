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

### ✅ Completed Tasks: Phase 1 (Auth & Gateway)
- [x] **Shared:** Write `shared/auth_utils.py` (password hashing with `passlib`, JWT generation/decoding).
- [x] **Auth Controllers:** Write `auth_controller.py` to handle user registration logic and duplicate email checks.
- [x] **Auth Routes:** Write `auth_routes.py` and attach to FastAPI app in `auth/main.py`.
- [x] **Gateway Middlewares:** Write `gateway/middlewares/auth_middleware.py` to intercept and validate JWT tokens from Unity.
- [x] **Gateway Proxy:** Write `gateway/controllers/proxy_controller.py` using `httpx` to forward Unity's requests to `localhost:8001` (Auth) and `localhost:8002` (Game).
- [x] **Gateway Routes:** Write `gateway/routes/proxy_routes.py` and attach to FastAPI app in `gateway/main.py`.

### ✅ Completed Tasks: Phase 2 & 3 (Gameplay & Traitors)
- [x] **Game Models:** Create `Question`, `Expert`, and `GameSession` Beanie models.
- [x] **Game Logic:** Implement session generation (picking questions, assigning personalities).
- [x] **Traitor System:** Add random assignment of the "Saboteur" role per session.
- [x] **Economy System:** Write endpoints to update User coins upon winning/losing.

### ✅ Completed Tasks: Phase 3.5 (Redis & Optimization)
- [x] **Redis Setup:** Create `shared/redis_client.py` connection manager using `redis`.
- [x] **Game Session Cache:** Cache active sessions in Redis (key: `game_session:{id}`, TTL: 30 min).
- [x] **Rate Limiting:** Add rate limiting middleware in Gateway (100 req/min per Firebase UID).
- [x] **Leaderboard:** Implement Redis sorted set for top 100 players by score.
- [x] **Monitoring:** Add Redis health check endpoint (`/health/redis`).

### ✅ Completed Tasks: Phase 4 (LLM Integration)
- [x] **LLM Logic:** Integrate LangChain/Groq for dynamic responses (`llm_client.py`).
- [x] **Prompt Engineering:** Create specific personality prompts (Historian, Risky, Saboteur).
- [x] **Streaming:** Stream responses to Gateway -> Unity.

### ✅ Completed Tasks: Phase 5 (Real-Time News Trivia with LangGraph & MCP)
- [x] **Graph Setup:** Initialize LangGraph state and workflow.
- [x] **Agent Nodes:** Build Research, Writer, and Validator nodes.
- [x] **Data Pipeline:** Save generated questions to the database tagged with "Current Events".
- [x] **Unity Updates:** Add UI for "Daily News" category and on-demand generation loading states.

### ✅ Completed Tasks: Unity (Frontend)
- [x] **Setup:** Create new 2D project, setup scene structure.
- [x] **UI:** Build Login/Register Canvas.
- [x] **Networking:** Create `FirebaseAuthManager.cs` to handle auth.
- [x] **UI:** Build Gameplay Canvas (Question text, 4 buttons, 3 Expert panels).
- [x] **Networking:** Create `GameNetworkManager.cs` to fetch questions and expert opinions.
- [x] **UI/UX:** Add post-game summary (Traitors revealed, Coins earned).
- [x] **Networking:** Implement streaming text handler for LLM responses.

### ⏳ Pending Tasks: Phase 6 (Real-Time Multiplayer)
- [ ] **WebSockets:** Add FastAPI WebSocket endpoint to `game_routes.py`.
- [ ] **Redis Pub/Sub:** Configure Redis to broadcast messages between server instances.
- [ ] **Matchmaking:** Implement a Redis-backed player queue (e.g. `LPOP/RPUSH`).
- [ ] **Multiplayer Session Logic:** Create `MultiplayerGameSession` that enforces the server-driven game clock.
- [ ] **Unity WebSocket Client:** Implement `NativeWebSocket` in Unity to maintain persistent connection.
- [ ] **Unity Matchmaking UI:** Create a "Find Match" loading screen that waits for the server's 'Match Found' event.
- [ ] **Unity Game UI:** Update gameplay UI to show dual scores and a countdown timer.
