from sqlalchemy.orm import Session as SyncSession # Keep for type hinting if needed, but operations are async
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from . import models, database

async def get_product_by_id(db: AsyncSession, product_id: int) -> models.Product | None:
    result = await db.execute(select(database.ProductDB).filter(database.ProductDB.id == product_id))
    return result.scalars().first()

async def get_product_by_name(db: AsyncSession, name: str) -> models.Product | None:
    result = await db.execute(select(database.ProductDB).filter(database.ProductDB.name == name))
    return result.scalars().first()

async def get_products(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[models.Product]:
    result = await db.execute(select(database.ProductDB).offset(skip).limit(limit))
    return result.scalars().all()

async def search_products(db: AsyncSession, query: str, skip: int = 0, limit: int = 100) -> list[models.Product]:
    search_term = f"%{query}%"
    result = await db.execute(
        select(database.ProductDB)
        .filter(
            or_(
                database.ProductDB.name.ilike(search_term),
                database.ProductDB.description.ilike(search_term),
            )
        )
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def add_product(db: AsyncSession, product: models.ProductCreate) -> models.Product:
    db_product = database.ProductDB(**product.model_dump())
    db.add(db_product)
    await db.flush()  # Use flush to get ID before commit if needed, or if commit is handled by get_db
    await db.refresh(db_product)
    return db_product

async def remove_product(db: AsyncSession, product_id: int) -> models.Product | None:
    db_product = await get_product_by_id(db, product_id) # Reuse existing async function
    if db_product:
        # SQLAlchemy ORM objects need to be deleted from the session they are bound to.
        # If get_product_by_id returns an ORM object from a different session context, 
        # it might cause issues. Best to fetch and delete in the same session context.
        # For simplicity here, assuming get_product_by_id gives us what we need for delete context.
        # However, the ProductDB instance returned from get_product_by_id is what we need to delete.
        
        # To be absolutely sure, let's fetch the object again in the current session for deletion
        to_delete_result = await db.execute(select(database.ProductDB).filter(database.ProductDB.id == product_id))
        to_delete_db_product = to_delete_result.scalars().first()
        if to_delete_db_product:
            await db.delete(to_delete_db_product)
            await db.flush()
            return to_delete_db_product # Return the object that was deleted
    return None

async def order_product(db: AsyncSession, order_details: models.ProductOrderRequest) -> models.Order:
    result = await db.execute(select(database.ProductDB).filter(database.ProductDB.id == order_details.product_id))
    db_product = result.scalars().first()

    if not db_product:
        raise ValueError(f"Product with id {order_details.product_id} not found.")

    if db_product.inventory < order_details.quantity:
        raise ValueError(
            f"Not enough inventory for product '{db_product.name}'. Available: {db_product.inventory}, Requested: {order_details.quantity}"
        )

    db_product.inventory -= order_details.quantity

    db_order = database.OrderDB(
        product_id=order_details.product_id,
        quantity=order_details.quantity,
        customer_identifier=order_details.customer_identifier,
    )
    db.add(db_order)
    db.add(db_product) # Add updated product back to session to track inventory change
    
    await db.flush()
    await db.refresh(db_order)
    await db.refresh(db_product)
    return db_order 