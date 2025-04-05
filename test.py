from utils.etl_modules import ParsePharmaciesInfo, ParseUserInfo
import json
import asyncio

async def main():
    with open("./data/users.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    for ele in data:
        user_info = ParseUserInfo(ele)
        async for d in user_info.get_user_purchase_history():
            print(d)
        
        
if __name__ == "__main__":
    # test
    asyncio.run(main())