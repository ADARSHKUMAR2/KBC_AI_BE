from fastapi import APIRouter, Request
from backend.gateway.controllers.proxy_controller import ProxyController

router = APIRouter()
proxy_controller = ProxyController()

@router.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_to_auth(request: Request, path: str):
    """
    Catch all requests to /auth/* and forward to Auth Service.
    
    Examples:
    - POST /auth/verify → Auth Service
    - GET /auth/profile → Auth Service
    
    The {path:path} captures everything after /auth/
    """
    return await proxy_controller.route_to_auth_service(request, f"/auth/{path}")

@router.api_route("/game/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_to_game(request: Request, path: str):
    """Forward game-related requests (Phase 2)"""
    return await proxy_controller.route_to_game_service(request, f"/game/{path}")
