from utils.db_models import Pharmacies, PharmaciesCash, PharmaciesMask, Users, UsersPurchaseHistory
from utils.etl_modules import ParsePharmaciesInfo, ParseUserInfo
import json
from utils.db_models import Base
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import inspect
from contextlib import asynccontextmanager
from sqlalchemy.orm import sessionmaker
import asyncio
from sqlalchemy import text
from utils.logger import logger
from typing import AsyncGenerator


class DatabaseConfig:
    def __init__(self, user: str, password: str, host: str, port: int, db_name: str):
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.db_name = db_name


    @property
    def async_database_url(self):
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/postgres"


    @property
    def sync_database_url(self):
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/postgres"



class DatabaseManager:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.engine = None
        self.session_factory = None

    

    async def init_pool(self):
        self.engine = create_async_engine(self.config.async_database_url, pool_size=10, max_overflow=20, isolation_level="AUTOCOMMIT", echo=True)
        self.session_factory = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        logger.info("SQLAlchemy pool initialized")

    
    async def init_sync_tables(self):
        async with self.engine.begin() as conn:
            try:
                table_names = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
                if table_names:
                    for table_name in table_names:
                        await conn.execute(text(f'DROP TABLE "{table_name}" CASCADE'))
                        logger.info(f"Table {table_name} has been removed.")
                else:
                    logger.info("No tables found in the database.")
            except Exception as e:
                logger.error(f"Error removing tables: {e}")
                raise e
            
            
    async def check_n_create_tables(self):
        async with self.engine.begin() as conn:
            result = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
            logger.info(f'There are {len(result)} tables in the database: ')
            for table_name in result:
                logger.info(f"Table Name: {table_name}")
            

            # Check if tables exist
            tables_to_create = [
                table_name for table_name in Base.metadata.tables.keys() if table_name not in result
            ]
            
            # Create tables if they do not exist
            if tables_to_create:
                logger.info(f"Does not exist table: {tables_to_create} Creating...")
                try:
                    await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=[Base.metadata.tables[table_name] for table_name in tables_to_create]))
                    logger.info("Tables created successfully")
                    
                    result_after_creation = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
                    created_tables = [table_name for table_name in result_after_creation]

                    if created_tables:
                        logger.info(f"Successfully created tables: {created_tables}")
                    else:
                        logger.error("Failed to verify table creation. Some tables may not have been created.")
                        
                except Exception as e:
                    logger.error(f"Failed to create tables: {e}")
            else:
                logger.info("All the Table has been created !")

                   
    async def check_n_create_database(self):
        async with self.engine.begin() as conn:
            try:
                result = await conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :db_name"), {"db_name": self.config.db_name})
                if result.scalar():
                    logger.info(f"Database {self.config.db_name} already exists")
                else:
                    await conn.execute(text(f'CREATE DATABASE "{self.config.db_name}"'))
                    
                    # Check if the database was created successfully
                    result_check = await conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :db_name"), {"db_name": self.config.db_name})
                    if result_check.scalar():
                        logger.info(f"Database {self.config.db_name} has been created")
                    else:
                        logger.error(f"Database {self.config.db_name} creation failed")
            except Exception as e:
                logger.info(f"Can not connect to PostgreSQL. Please check your configuration: {type(e).__name__}, {e}")

    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Provide a session for database operations."""
        if not self.session_factory:
            raise RuntimeError("Session factory is not initialized.")
        
        async with self.session_factory() as session:
            yield session
    
    
    async def insert_data(self, model_class: object, data: dict) -> int:
        try:
            async with self.get_session() as session:
                obj = model_class(**data)
                session.add(obj)
                await session.flush()
                await session.commit()
                logger.info(f"Created {model_class.__name__} ID: {obj.id}")
        except Exception as e:
            await session.rollback()
            logger.error(f"Error inserting {model_class.__name__}: {e}")
            return None
         
            
    async def close(self) -> None:
        if self.engine:
            await self.engine.dispose()
            logger.info("SQLAlchemy pool disposed")


async def get_db() -> DatabaseManager:
    from time import sleep
    db_config = DatabaseConfig(
        user="postgres",
        password="admin",
        host="localhost",
        port=55688,
        db_name="mydatabase"
    )

    db_manager = DatabaseManager(db_config)

    try:
        await db_manager.init_pool()
        await db_manager.init_sync_tables()
        logger.info("Database pool & tables initialized")
        sleep(0.5)
        await db_manager.check_n_create_database()
        await db_manager.check_n_create_tables()
        return db_manager
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return None


def load_json_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error loading {file_path}: {e}")
        return None
    

        
async def Insert_pharmacies_data_to_db():
    db_manager = await get_db()
    # users_data = load_json_file("./data/users.json")
    pharmacies_data = load_json_file("./data/pharmacies.json")
    
    if db_manager:
        for pharmacy in pharmacies_data:
            pharmacy_info = ParsePharmaciesInfo(pharmacy)
            pharmacy_openning_info = await pharmacy_info.get_pharmacy_opening_info()
            for opening_info in pharmacy_openning_info:
                await db_manager.insert_data(Pharmacies, opening_info)

            pharmacy_cash_info = await pharmacy_info.get_pharmacy_cash_balance()
            await db_manager.insert_data(PharmaciesCash, pharmacy_cash_info)
            
            pharmacy_mask_info = await pharmacy_info.get_mask_info()
            for mask_info in pharmacy_mask_info:
                await db_manager.insert_data(PharmaciesMask, mask_info)
            


if __name__ == "__main__":
    # init_tables()
    asyncio.run(get_db())
 