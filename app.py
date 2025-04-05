from fastapi import FastAPI, Depends
from sqlalchemy import text
from contextlib import asynccontextmanager
from save_data_to_db import DatabaseManager, get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_manager = await get_db()  
    await db_manager.check_n_create_database()
    yield
    await db_manager.close()  


app = FastAPI(lifespan=lifespan)


@app.get("/users/{user_id}")
async def get_user(user_id: int, db_manager: DatabaseManager = Depends(get_db)):
    async with db_manager.get_session() as session:
        result = await session.execute(text("SELECT * FROM users WHERE id = :id"), {'id': user_id})
        user = result.fetchone()
        if user:
            return {"user_id": user[0], "name": user[1]}
        return {"message": "User not found"}


@app.get("/")
async def read_root():
    return {"message": "Welcome to the phantom mask API"}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000, reload=True)

