import httpx
from typing import Dict, Any

class ServiceProxy:
    """
    Forwards requests from Gateway to backend services.
    
    Why use a proxy?
    - Unity only talks to Gateway (single entry point)
    - Gateway routes to correct microservice
    - Adds authentication layer
    - Enables load balancing, rate limiting, logging
    """
    
    def __init__(self):
        # HTTP client with connection pooling
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def forward_request(
        self,
        method: str,
        service_url: str,
        path: str,
        headers: Dict[str, str] = None,
        json_data: Dict[str, Any] = None,
        query_params: Dict[str, str] = None
    ):
        """
        Forward HTTP request to a backend service.
        
        Args:
            method: GET, POST, PUT, DELETE, etc.
            service_url: Base URL of service (e.g., http://localhost:8001)
            path: Endpoint path (e.g., /auth/profile)
            headers: HTTP headers to forward
            json_data: Request body (for POST/PUT)
            query_params: URL parameters
            
        Returns:
            Response from the backend service
        """
        url = f"{service_url}{path}"
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                headers=headers,
                json=json_data,
                params=query_params
            )
            
            return response
            
        except httpx.RequestError as e:
            raise Exception(f"Service communication error: {str(e)}")
    
    async def close(self):
        """Close HTTP client on shutdown"""
        await self.client.aclose()
