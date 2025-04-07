import asyncpg
import asyncio

async def fetch_pharmacies_mask():
    conn = await asyncpg.connect(
        user='postgres',
        password='admin',
        database='mydatabase',
        host='localhost',
        port=5432
    )

    rows = await conn.fetch('SELECT * FROM "pharmacies_mask";')
    await conn.close()
    
    for row in rows:
        print(dict(row))

asyncio.run(fetch_pharmacies_mask())
