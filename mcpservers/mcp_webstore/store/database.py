import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Text, ForeignKey, inspect, Numeric
from sqlalchemy.orm import relationship


# DATABASE_URL = "postgresql+asyncpg://user:password@host:port/database"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://myuser:mypassword@127.0.0.1:5432/store_db")

engine = create_async_engine(DATABASE_URL, echo=False) # echo=True for debugging SQL

# expire_on_commit=False will prevent attributes from being expired
# after commit, which is useful for async code.
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

# SQLAlchemy models
class ProductDB(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    description = Column(Text, nullable=True)
    inventory = Column(Integer, default=0)
    price = Column(Numeric(10, 2), nullable=False, server_default='0.00')

    orders = relationship("OrderDB", back_populates="product")

class OrderDB(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    customer_identifier = Column(String)

    product = relationship("ProductDB", back_populates="orders")

# Function to create tables (now async)
async def create_db_and_tables():
    async with engine.begin() as conn:
        # Check if tables exist (optional, but good practice to avoid errors on re-runs if not using migrations)
        # For simplicity, we'll just run create_all. For production, Alembic is better.
        # def table_exists(conn, table_name):
        #     return inspect(conn).has_table(table_name)
        # if not await conn.run_sync(table_exists, "products"):
        #    await conn.run_sync(Base.metadata.create_all, tables=[ProductDB.__table__])
        # if not await conn.run_sync(table_exists, "orders"):
        #    await conn.run_sync(Base.metadata.create_all, tables=[OrderDB.__table__])
        await conn.run_sync(Base.metadata.create_all)
    print("INFO:     Database tables checked/created.")

# Dependency to get DB session (now async)
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit() # Commit if no exceptions were raised by the endpoint
        except Exception:
            await session.rollback() # Rollback on error
            raise
        finally:
            await session.close() # Not strictly necessary with async context manager, but good practice 