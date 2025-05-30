from mcp.server.fastmcp import FastMCP
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from appservers.store import crud, models as PydanticModels, database
import asyncio

mcp_server = FastMCP()

def get_db_session():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@mcp_server.tool()
async def get_products(skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """Fetches a list of all products from the database."""
    db_gen = get_db_session()
    db: Session = next(db_gen)
    try:
        products = crud.get_products(db, skip=skip, limit=limit)
        return [PydanticModels.Product.model_validate(p).model_dump() for p in products]
    finally:
        next(db_gen, None) # ensure db is closed

@mcp_server.tool()
async def get_product_by_id(product_id: int) -> Optional[Dict[str, Any]]:
    """Fetches a single product by its ID from the database."""
    db_gen = get_db_session()
    db: Session = next(db_gen)
    try:
        product = crud.get_product_by_id(db, product_id=product_id)
        if product:
            return PydanticModels.Product.model_validate(product).model_dump()
        return None
    finally:
        next(db_gen, None)

@mcp_server.tool()
async def get_product_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Fetches a single product by its name from the database."""
    db_gen = get_db_session()
    db: Session = next(db_gen)
    try:
        product = crud.get_product_by_name(db, name=name)
        if product:
            return PydanticModels.Product.model_validate(product).model_dump()
        return None
    finally:
        next(db_gen, None)

@mcp_server.tool()
async def search_products(query: str, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """Searches for products in the database based on a query string (name or description)."""
    db_gen = get_db_session()
    db: Session = next(db_gen)
    try:
        products = crud.search_products(db, query=query, skip=skip, limit=limit)
        return [PydanticModels.Product.model_validate(p).model_dump() for p in products]
    finally:
        next(db_gen, None)

@mcp_server.tool()
async def add_product(name: str, description: Optional[str] = None, inventory: int = 0) -> Dict[str, Any]:
    """Adds a new product to the database."""
    product_create = PydanticModels.ProductCreate(name=name, description=description, inventory=inventory)
    db_gen = get_db_session()
    db: Session = next(db_gen)
    try:
        product = crud.add_product(db, product=product_create)
        return PydanticModels.Product.model_validate(product).model_dump()
    finally:
        next(db_gen, None)

@mcp_server.tool()
async def remove_product(product_id: int) -> Optional[Dict[str, Any]]:
    """Removes a product from the database by its ID."""
    db_gen = get_db_session()
    db: Session = next(db_gen)
    try:
        product = crud.remove_product(db, product_id=product_id)
        if product:
            return PydanticModels.Product.model_validate(product).model_dump()
        return None
    finally:
        next(db_gen, None)

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
    db_gen = get_db_session()
    db: Session = next(db_gen)
    try:
        order = crud.order_product(db, order_details=order_request)
        return PydanticModels.Order.model_validate(order).model_dump()
    except ValueError as e:
        # FastMCP might handle exceptions automatically, or you might want to return a specific error structure
        # For now, re-raising to let FastMCP handle it or be caught by a higher level.
        raise
    finally:
        next(db_gen, None)

async def mcp_store_startup():
    print("INFO:     MCP Store Server starting up...")
    await database.create_db_and_tables()
    print("INFO:     MCP Store database tables checked/created.")
    # Any other async startup tasks for the MCP server can go here.

async def mcp_store_load_tools():
    print("INFO:     MCP Store Server loading tools...")
    tools = await mcp_server.list_tools()
    print("INFO:     MCP Store Server loaded tools:", *map(lambda x: x.name, tools))

if __name__ == "__main__":
    # Run async startup tasks
    asyncio.run(mcp_store_startup())
    asyncio.run(mcp_store_load_tools())

    # After async startup, proceed with FastMCP server initialization/run
    # This part is dependent on how your FastMCP server is actually started.
    # For example, if it has a blocking run method:
    # mcp_server.run(host="0.0.0.0", port=8002) # Example: Replace with actual FastMCP server run command
    mcp_server.run()