from mcp.server.fastmcp import FastMCP
import httpx
from typing import List, Dict, Any, Optional
import os

# Initialize FastMCP
mcp_server = FastMCP()

# Initialize FastMCP in japanese
# エムシーピーサーバー = ファストエムシーピー()

STORE_SERVER_URL = os.getenv("STORE_SERVER_URL", "http://localhost:8001")

# HTTP client (using httpx)
# TODO: It's good practice to use a client instance for connection pooling, etc.
async_client = httpx.AsyncClient(base_url=STORE_SERVER_URL)

async def make_api_request(method: str, endpoint: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None) -> Dict[str, Any]:
    """Helper function to make API requests to the Store Server."""
    try:
        response = await async_client.request(method, endpoint, params=params, json=json_data)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        return response.json()
    except httpx.HTTPStatusError as e:
        # Attempt to get more details from the response body if available
        error_detail = e.response.json().get("detail", e.response.text) if e.response.content else str(e)
        raise ValueError(f"API Error: {e.response.status_code} - {error_detail} when calling {e.request.method} {e.request.url}") from e
    except httpx.RequestError as e:
        raise ValueError(f"Request Error: Could not connect to Store Server at {e.request.url}. Details: {str(e)}") from e

@mcp_server.tool()
async def get_products(skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """Fetches a list of all products from the Store Server API."""
    return await make_api_request("GET", "/products/", params={"skip": skip, "limit": limit})

@mcp_server.tool()
async def get_product_by_id(product_id: int) -> Optional[Dict[str, Any]]:
    """Fetches a single product by its ID from the Store Server API."""
    try:
        return await make_api_request("GET", f"/products/id/{product_id}")
    except ValueError as e:
        if "404" in str(e): # crude check for 404
            return None # Product not found
        raise

@mcp_server.tool()
async def get_product_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Fetches a single product by its name from the Store Server API."""
    try:
        return await make_api_request("GET", f"/products/name/{name}")
    except ValueError as e:
        if "404" in str(e):
            return None # Product not found
        raise

@mcp_server.tool()
async def search_products(query: str, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """Searches for products via the Store Server API based on a query string."""
    try:
        return await make_api_request("GET", "/products/search/", params={"query": query, "skip": skip, "limit": limit})
    except ValueError as e:
        if "404" in str(e): # crude check for 404 when no products found
            return [] 
        raise

@mcp_server.tool()
async def add_product(name: str, description: Optional[str] = None, inventory: int = 0) -> Dict[str, Any]:
    """Adds a new product via the Store Server API."""
    payload = {"name": name, "description": description, "inventory": inventory}
    return await make_api_request("POST", "/products/", json_data=payload)

@mcp_server.tool()
async def remove_product(product_id: int) -> Optional[Dict[str, Any]]:
    """Removes a product by its ID via the Store Server API."""
    try:
        return await make_api_request("DELETE", f"/products/{product_id}")
    except ValueError as e:
        if "404" in str(e):
            return None # Product not found
        raise 

@mcp_server.tool()
async def order_product(product_id: int, quantity: int, customer_identifier: str) -> Dict[str, Any]:
    """Places an order for a product via the Store Server API.
    Raises ValueError if product not found, insufficient inventory, or other API error.
    """
    payload = {"product_id": product_id, "quantity": quantity, "customer_identifier": customer_identifier}
    return await make_api_request("POST", "/orders/", json_data=payload)

# TODO: managed async client lifecycle
# @mcp_server.on_event("startup")
# async def startup_event():
#     global async_client
#     async_client = httpx.AsyncClient(base_url=STORE_SERVER_URL)

# @mcp_server.on_event("shutdown")
# async def shutdown_event():
#     await async_client.close() 

if __name__ == "__main__":
    mcp_server.settings.port = 8001
    mcp_server.run(transport="sse")
