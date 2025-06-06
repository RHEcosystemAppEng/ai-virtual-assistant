from mcp.server.fastmcp import FastMCP
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from . import crud, models as PydanticModels, database
import asyncio

mcp_server = FastMCP()

@mcp_server.tool()
async def get_products(skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """Fetches a list of all products from the database."""
    async with database.AsyncSessionLocal() as session:
        db_products = await crud.get_products(session, skip=skip, limit=limit)
        return [PydanticModels.Product.model_validate(p).model_dump() for p in db_products]

@mcp_server.tool()
async def get_product_by_id(product_id: int) -> Optional[Dict[str, Any]]:
    """Fetches a single product by its ID from the database."""
    async with database.AsyncSessionLocal() as session:
        db_product = await crud.get_product_by_id(session, product_id=product_id)
        if db_product:
            return PydanticModels.Product.model_validate(db_product).model_dump()
        return None

@mcp_server.tool()
async def get_product_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Fetches a single product by its name from the database."""
    async with database.AsyncSessionLocal() as session:
        db_product = await crud.get_product_by_name(session, name=name)
        if db_product:
            return PydanticModels.Product.model_validate(db_product).model_dump()
        return None

@mcp_server.tool()
async def search_products(query: str, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """Searches for products in the database based on a query string (name or description)."""
    async with database.AsyncSessionLocal() as session:
        db_products = await crud.search_products(session, query=query, skip=skip, limit=limit)
        return [PydanticModels.Product.model_validate(p).model_dump() for p in db_products]

@mcp_server.tool()
async def add_product(name: str, description: Optional[str] = None, inventory: int = 0, price: float = 0.0) -> Dict[str, Any]:
    """Adds a new product to the database."""
    product_create = PydanticModels.ProductCreate(name=name, description=description, inventory=inventory, price=price)
    async with database.AsyncSessionLocal() as session:
        db_product = await crud.add_product(session, product=product_create)
        await session.commit()
        return PydanticModels.Product.model_validate(db_product).model_dump()

@mcp_server.tool()
async def remove_product(product_id: int) -> Optional[Dict[str, Any]]:
    """Removes a product from the database by its ID."""
    async with database.AsyncSessionLocal() as session:
        db_product = await crud.remove_product(session, product_id=product_id)
        if db_product:
            await session.commit()
            return PydanticModels.Product.model_validate(db_product).model_dump()
        return None

@mcp_server.tool()
async def order_product(product_id: int, quantity: int, customer_identifier: str) -> Dict[str, Any]:
    """Places an order for a product. 
    This involves checking inventory, deducting the quantity from the product's inventory, 
    and creating an order record in the database.
    Raises ValueError if product not found or insufficient inventory.
    """
    order_request = PydanticModels.ProductOrderRequest(
        product_id=product_id, 
        quantity=quantity, 
        customer_identifier=customer_identifier
    )
    async with database.AsyncSessionLocal() as session:
        try:
            db_order = await crud.order_product(session, order_details=order_request)
            await session.commit()
            return PydanticModels.Order.model_validate(db_order).model_dump()
        except ValueError: 
            await session.rollback()
            raise
        except Exception: 
            await session.rollback()
            raise

async def run_startup_tasks():
    print("INFO:     MCP_DBStore Server startup tasks beginning...")
    await database.create_db_and_tables()
    print("INFO:     MCP_DBStore database tables checked/created.")
    print("INFO:     MCP_DBStore Server core initialization complete.")

if __name__ == "__main__":
    asyncio.run(run_startup_tasks())
    print("INFO:     Starting MCP_DBStore FastMCP server on port 8002...")
    mcp_server.settings.port = 8002
    mcp_server.run(transport="sse")