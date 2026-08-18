from fastapi import Request, HTTPException
from backend.gateway.utils.http_client import ServiceProxy
import os

class ProxyController:
    """
    Routes incoming requests to the correct microservice.
    
    Routing table:
    /auth/* → Auth Service (port 8001)
    /game/* → Game Service (port 8002)
    """
    
    def __init__(self):
        self.proxy = ServiceProxy()
        
        # Service URLs from environment variables
        self.auth_service_url = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
        self.game_service_url = os.getenv("GAME_SERVICE_URL", "http://localhost:8002")
    
    async def route_to_auth_service(self, request: Request, path: str):
        """
        Forward requests to Auth Service.
        
        Example: 
        Unity calls: GET http://localhost:8000/auth/profile
        Gateway forwards: GET http://localhost:8001/auth/profile
        """
        return await self._forward_request(
            request=request,
            service_url=self.auth_service_url,
            path=path
        )
    
    async def route_to_game_service(self, request: Request, path: str):
        """Forward requests to Game Service (Phase 2)"""
        return await self._forward_request(
            request=request,
            service_url=self.game_service_url,
            path=path
        )
    
    async def _forward_request(self, request: Request, service_url: str, path: str):
        """
        Internal method to forward any request.
        
        Preserves:
        - HTTP method (GET/POST/etc.)
        - Headers (including Authorization)
        - Request body
        - Query parameters
        """
        # Get request body if present
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.json() if await request.body() else None
        
        # Forward the request
        try:
            response = await self.proxy.forward_request(
                method=request.method,
                service_url=service_url,
                path=path,
                headers=dict(request.headers),
                json_data=body,
                query_params=dict(request.query_params)
            )
            
            # Return the same response from the service
            return response.json()
            
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Service unavailable: {str(e)}")
    
    async def cleanup(self):
        """Close connections on shutdown"""
        await self.proxy.close()
