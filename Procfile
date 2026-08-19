gateway: PORT=8000 FORCE_COLOR=1 PYTHONUNBUFFERED=1 PYTHONPATH=. uv run python -m backend.gateway.main
auth: PORT=8001 FORCE_COLOR=1 PYTHONUNBUFFERED=1 PYTHONPATH=. uv run python -m backend.services.auth.main
game: PORT=8002 FORCE_COLOR=1 PYTHONUNBUFFERED=1 PYTHONPATH=. uv run python -m backend.services.game.main
seed: FORCE_COLOR=1 PYTHONUNBUFFERED=1 PYTHONPATH=. uv run python -m backend.services.game.data.seed_questions && echo "Seed complete. Press Ctrl+C to continue." && sleep infinity
