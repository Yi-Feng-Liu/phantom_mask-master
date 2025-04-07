from utils.db_models import Pharmacies, PharmaciesCash, PharmaciesMask, Users, UsersPurchaseHistory
from utils.etl_modules import ParsePharmaciesInfo, ParseUserInfo
from utils.db_models import Base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import inspect, text
from contextlib import asynccontextmanager
from sqlalchemy.orm import sessionmaker
from utils.logger import logger
from typing import AsyncGenerator
import json
import asyncio
from sqlalchemy.future import select


class DatabaseConfig:
    def __init__(self, user: str, password: str, host: str, port: int, db_name: str):
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.db_name = db_name


    @property
    def async_database_url(self):
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/mydatabase"


    @property
    def sync_database_url(self):
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/mydatabase"



class DatabaseManager:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.engine = None
        self.session_factory = None

    

    async def init_pool(self):
        self.engine = create_async_engine(self.config.async_database_url, pool_size=10, max_overflow=20, isolation_level="AUTOCOMMIT", echo=True)
        self.session_factory = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        logger.info("SQLAlchemy pool initialized")

    
    async def del_tables(self):
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
        try:
            async with self.engine.begin() as conn:
                result = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
                logger.info(f'There are {len(result)} tables in the database.')

                tables_to_create = [
                    table_name for table_name in Base.metadata.tables.keys() if table_name not in result
                ]

                if tables_to_create:
                    logger.info(f"Missing tables: {tables_to_create}. Creating...")
                    await conn.run_sync(lambda sync_conn: Base.metadata.create_all(
                        sync_conn, tables=[Base.metadata.tables[table_name] for table_name in tables_to_create]
                    ))
                    logger.info("Tables created successfully.")

                else:
                    logger.info("All tables are already created!")

        except Exception as e:
            logger.error(f"An error occurred: {e}")

                   
    async def check_n_create_database(self):
        async with self.engine.begin() as conn:
            try:
                db_name = "mydatabase"
                result = await conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                    {"db_name": db_name}
                )
                if result.scalar():
                    logger.info(f"Database {db_name} already exists")
                else:
                    await conn.execute(text(f'CREATE DATABASE "{db_name}"'))

                    result_check = await conn.execute(
                        text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                        {"db_name": db_name}
                    )
                    if result_check.scalar():
                        logger.info(f"Database {db_name} has been created")
                    else:
                        logger.error(f"Database {db_name} creation failed")
            except Exception as e:
                logger.error(f"Cannot connect to PostgreSQL. Please check your configuration: {type(e).__name__}, {e}")


    
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



async def get_db(first_time_execute: bool|None=None) -> DatabaseManager:
    db_config = DatabaseConfig(
        user="postgres",
        password="admin",
        host="localhost",
        port=5432,
        db_name="mydatabase"
    )

    db_manager = DatabaseManager(db_config)

    try:
        if first_time_execute is None or first_time_execute == False:
            await db_manager.init_pool()
        if first_time_execute:
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
    db_manager = await get_db(first_time_execute=False)
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


async def Insert_users_data_to_db():
    db_manager = await get_db(first_time_execute=False)
    users_data = load_json_file("./data/users.json")
    if db_manager:
        async with db_manager.get_session() as session:
            for user in users_data:
                user_info = ParseUserInfo(user)
                user_cash_info = await user_info.get_user_n_balance_info()
                await db_manager.insert_data(Users, user_cash_info)

                
                purchase_history = user_info.get_user_purchase_history()
                async for history in purchase_history:
                    # Step 1: Query the Users table to retrieve the corresponding ID for the user_id
                    result = await session.execute(
                        select(Users).filter(Users.name == history["user_id"])
                    )
                    user = result.scalars().first() 
                    if user is None:
                        raise Exception("User not found")

                    # Step 2: Query the Pharmacies table to retrieve the corresponding ID for the pharmacies_id
                    result = await session.execute(
                        select(Pharmacies).filter(Pharmacies.name == history["pharmacies"])
                    )
                    pharmacy = result.scalars().first() 
                    if pharmacy is None:
                        raise Exception("Pharmacy not found")

                    # Step 3: Query the pharmacies_mask table to retrieve the corresponding ID for the pharmacies_mask_id
                    mask_data = history["pharmacies_mask"]
                    result = await session.execute(
                        select(PharmaciesMask).filter(
                            PharmaciesMask.mask_name == mask_data["mask_name"],
                            PharmaciesMask.mask_color == mask_data["mask_color"],
                            PharmaciesMask.pack_quantity == mask_data["pack_quantity"]
                        )
                    )
                    pharmacy_mask = result.scalars().first() 
                    if pharmacy_mask is None:
                        raise Exception("Mask not found")

                    # Step 4: Prepare to insert updated data into the UsersPurchaseHistory table
                    new_purchase_history = {
                        "user_id": user.id,
                        "pharmacies": pharmacy.id,
                        "pharmacies_mask": pharmacy_mask.id,
                        "trn_amount": history["trn_amount"],
                        "trn_date": history["trn_date"]
                    }
                    
                    await db_manager.insert_data(UsersPurchaseHistory, new_purchase_history)



async def main():
    await get_db(first_time_execute=True)
    await Insert_pharmacies_data_to_db()
    await Insert_users_data_to_db()




if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())



 
