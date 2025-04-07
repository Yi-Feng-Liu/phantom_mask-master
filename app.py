from fastapi import FastAPI, Depends, Query, HTTPException
from sqlalchemy.sql.expression import func
from contextlib import asynccontextmanager
from save_data_to_db import get_db, DatabaseManager
from sqlalchemy.future import select
from typing import  Optional
from datetime import datetime, date
from decimal import Decimal
from utils.db_models import Pharmacies, PharmaciesCash, PharmaciesMask, Users, UsersPurchaseHistory


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_manager = await get_db()  
    await db_manager.check_n_create_database()
    yield
    await db_manager.close()  


app = FastAPI(lifespan=lifespan, title="Pharmacy & Mask API", description="API for managing pharmacies and mask transactions.")


@app.get("/")
async def read_root():
    return {"message": "Welcome to the phantom mask API"}


@app.get(
    path="/pharmacies/open", 
    summary="List pharmacies open at a specific time/day", 
    description="Get pharmacies that are open at a specified time and optionally on a specific day."
)
async def get_open_pharmacies(
    time: str = Query(..., description="Time in HH:MM format"),
    day: Optional[str] = Query(..., description="Day of the week, e.g., Mon, Tue..."),
    db_manager: DatabaseManager = Depends(get_db)
):
    async with db_manager.get_session() as db:
        stmt = select(Pharmacies).where(Pharmacies.open_time <= time, Pharmacies.close_time >= time)
        stmt = stmt.where(Pharmacies.opening_day == day)
        result = await db.execute(stmt)
        return result.scalars().all()

@app.get(
    path="/pharmacies/{pharmacy_name}/masks", 
    summary="List masks in a pharmacy", 
    description="List all masks sold by a given pharmacy, sorted by name or price."
)
async def list_masks_in_pharmacy(
    pharmacy_name: str,
    sort_by: str = Query("name", regex="^(name|price)$"),
    db_manager: DatabaseManager = Depends(get_db)
):
    async with db_manager.get_session() as db:
        stmt = select(PharmaciesMask).where(PharmaciesMask.name == pharmacy_name).order_by(getattr(PharmaciesMask, sort_by))
        result = await db.execute(stmt)
        return result.scalars().all()


@app.get(
    path="/pharmacies/mask_count", 
    summary="List pharmacies by mask count", 
    description="List pharmacies with more or less than x masks in a price range."
)
async def pharmacies_by_mask_count(
    operator: str = Query(..., regex="^(more|less)$"),
    count: int = Query(..., ge=0),
    min_price: Decimal = Query(0),
    max_price: Decimal = Query(10000),
    db_manager: DatabaseManager = Depends(get_db)
):
    async with db_manager.get_session() as db:
        stmt = select(Pharmacies.id, Pharmacies.name).join(PharmaciesMask, Pharmacies.name == PharmaciesMask.name)
        stmt = stmt.where(PharmaciesMask.price.between(min_price, max_price))
        result = await db.execute(stmt)
        rows = result.all()

        from collections import Counter
        counts = Counter([row.id for row in rows])

        if operator == "more":
            filtered = [pharmacy for pharmacy, c in counts.items() if c > count]
        else:
            filtered = [pharmacy for pharmacy, c in counts.items() if c < count]

        stmt = select(Pharmacies.name).where(Pharmacies.id.in_(filtered)).distinct() 
        result = await db.execute(stmt)
        return result.scalars().all()


@app.get(
    path="/users/top", 
    summary="Top users by transaction", 
    description="Return top X users ranked by total transaction amount within a date range."
)
async def top_users_by_transaction(
    top_x: int = Query(..., gt=0),
    start_date: date = Query(..., description="Start date in format YYYY-MM-DD"),
    end_date: date = Query(..., description="end_date date in format YYYY-MM-DD"),
    db_manager: DatabaseManager = Depends(get_db)
):
    async with db_manager.get_session() as db:
        stmt = select(Users.name, func.sum(UsersPurchaseHistory.trn_amount).label("total")).join(Users).where(
            UsersPurchaseHistory.trn_date.between(start_date, end_date)
        ).group_by(UsersPurchaseHistory.user_id, Users.id).order_by(func.sum(UsersPurchaseHistory.trn_amount).desc()).limit(top_x)
        result = await db.execute(stmt)
        top_users = {user[0]: user[1] for user in result.all()}
        return top_users



@app.get(
    path="/transactions/summary", 
    summary="Total masks and transaction value", 
    description="Get total number of transactions and total value in a date range."
)
async def transaction_summary(
    start_date: date = Query(..., description="Start date in format YYYY-MM-DD"),
    end_date: date = Query(..., description="Start date in format YYYY-MM-DD"),
    db_manager: DatabaseManager = Depends(get_db)
):
    async with db_manager.get_session() as db:
        stmt = select(func.count(UsersPurchaseHistory.id), func.sum(UsersPurchaseHistory.trn_amount)).where(
            UsersPurchaseHistory.trn_date.between(start_date, end_date)
        )
        result = await db.execute(stmt)
        count, total_amount = result.one_or_none()
        return {
            "total_transactions": count if count else 0,
            "total_value": total_amount if total_amount else 0.0
        }


@app.get(
    path="/search", 
    summary="Search pharmacies or masks", 
    description="Search pharmacies or masks by name, ranked by simple relevance."
)
async def search_items(
    keyword: str = Query(...),
    db_manager: DatabaseManager = Depends(get_db)
):
    async with db_manager.get_session() as db:
        stmt1 = select(Pharmacies.name).where(Pharmacies.name.ilike(f"%{keyword}%")).distinct()
        stmt2 = select(PharmaciesMask.mask_name).where(PharmaciesMask.mask_name.ilike(f"%{keyword}%")).distinct()
        result1 = await db.execute(stmt1)
        result2 = await db.execute(stmt2)
        return {
            "pharmacies": result1.scalars().all(),
            "masks": result2.scalars().all()
        }


# The purchase_mask API still has some bugs that need to be fixed
@app.post(
    path="/purchase", 
    summary="User purchases a mask", 
    description="Process a user purchasing a mask from a pharmacy. Updates balances and logs the transaction atomically."
)
async def purchase_mask(
    user_id: int = Query(...),
    pharmacy_id: int = Query(...),
    mask_id: int = Query(...),
    db_manager: DatabaseManager = Depends(get_db)
):
    async with db_manager.get_session() as db:
        async with db.begin():
            user = await db.get(Users, user_id)
            pharmacy = await db.get(PharmaciesCash, pharmacy_id)
            mask = await db.get(PharmaciesMask, mask_id)

            if not user or not mask or not pharmacy:
                raise HTTPException(status_code=404, detail="User, pharmacy or mask not found")

            if user.cash_balance < mask.price:
                raise HTTPException(status_code=400, detail="Insufficient balance")

            user.cash_balance -= mask.price

            cash_stmt = select(PharmaciesCash).where(PharmaciesCash.id == pharmacy_id, PharmaciesCash.id == mask_id)
            cash_result = await db.execute(cash_stmt)
            cash_entry = cash_result.scalar_one_or_none()

            if cash_entry:
                cash_entry.cash_balance += mask.price
            else:
                new_cash = PharmaciesCash(name=pharmacy_id, sold_item=mask_id, cash_balance=mask.price)
                db.add(new_cash)

            new_trn = UsersPurchaseHistory(
                user_id=user_id,
                pharmacies=pharmacy_id,
                pharmacies_mask=mask_id,
                trn_amount=mask.price,
                trn_date=datetime.now()
            )
            db.add(new_trn)
            
    return {"message": "Purchase successful"}



