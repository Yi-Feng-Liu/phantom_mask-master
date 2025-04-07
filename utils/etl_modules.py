import re
from typing import AsyncGenerator



class ParsePharmaciesInfo:
    def __init__(self, pharmacies_info: dict) -> None:
        self.pharmacies_info = pharmacies_info
        self.pharmacy_name = pharmacies_info.get("name")
        self.cash_balance = pharmacies_info.get("cashBalance")
    
    
    async def _parse_openingHours(self):
        days_map = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
        
        entries = self.pharmacies_info['openingHours'].split("/")
        data = []
        
        for entry in entries:
            match = re.match(r"(.*?)(\d{2}:\d{2}) - (\d{2}:\d{2})", entry.strip())
            if match:
                days_part, open_time, close_time = match.groups()
                days_part = days_part.strip()
                
                days = []
                for part in days_part.split(","):
                    part = part.strip()
                    if "-" in part:
                        start, end = part.split("-")
                        start, end = start.strip(), end.strip()
                        start_idx, end_idx = days_map.index(start), days_map.index(end)
                        days.extend([day for day in days_map[start_idx:end_idx+1]])
                    else:
                        days.append(part)
                
                for day in days:
                    data.append({
                        "opening_day": day,
                        "open_time": open_time,
                        "close_time": close_time
                    })
        return data


    
    async def get_pharmacy_opening_info(self) -> list[dict]:
        """
        Combines the basic information of the pharmacy with the parsed opening hours and returns a list of dictionaries, 
        where each dictionary contains all the necessary details for the `Pharmacy` table.

        Returns:
            dict: A dictionary containing the pharmacy's name, cash balance, and opening hours information.
        
        Example:
        >>> pharmacy_data
            {
                "name": "Pharmacy A",
                "openingHours": "Mon - Fri 08:00 - 17:00 / Sat, Sun 08:00 - 12:00"
            },
        >>> pharmacy_info = Parse_pharmacies_info(pharmacy_data)
        >>> pharmacy_info.get_pharmacy_opening_info
            [
                {"name": "Pharmacy A", "opening_day": "Monday", "open_Time": "08:00", "close_Time": "17:00"},
                {"name": "Pharmacy A", "opening_day": "Tuesday", "open_Time": "08:00", "close_Time": "17:00"},
                ...
            ]
        """
        add_info = {
            'name': self.pharmacy_name,
        }
        opening_data_list = await self._parse_openingHours()
        pharmacy_infos = [{**add_info, **opening_data} for opening_data in opening_data_list]
        return pharmacy_infos
    
    
    async def get_pharmacy_cash_balance(self) -> dict:
        """ For the `PharmacyCashInfo` table """
        return {
            "name": self.pharmacy_name,
            "cash_balance": self.cash_balance
        }


    async def _parse_mask_info(self, mask_info: dict|str, pharmacy_name: str|None = None) -> dict:
        """
        Parses mask information including name, color, pack quantity, and price.

        Args:
            mask_info (dict|str): A dictionary containing:
                - name (str): A string describing the mask in the expected format.
                - price (float): The price of the mask.

        Raises:
            ValueError: If the input string does not match the expected format.

        Returns:
            dict: A dictionary containing:
                - name (str): The name of the pharmacy.
                - mask_name (str): The name of the mask.
                - mask_color (str): The color of the mask.
                - pack_quantity (int): The number of masks per pack.
                - price (float): The price of the mask.

        Example:
            >>> _parse_mask_info({"name": "Second Smile (black) (10 per pack)", "price": 15.99})
            {
                'name': 'First Care Rx', 
                'mask_name': 'Second Smile', 
                'mask_color': 'black', 
                'pack_quantity': 10, 
                'price': 15.99
            }
        """
        pattern = r"^(.*?)\s*\((.*?)\)\s*\((\d+) per pack\)$"
        mask_price = None
        
        if isinstance(mask_info, dict):
            mask_string = mask_info['name']
            mask_price = mask_info['price']
            
        elif isinstance(mask_info, str):
            mask_string = mask_info
        
        else:
            raise ValueError(f"Invalid mask info format: {mask_info}")
        
        match = re.match(pattern, mask_string)
        
        if match:
            mask_name = match.group(1).strip()  # extract mask name
            mask_color = match.group(2).strip()  # extract mask color
            pack_quantity = int(match.group(3))  # convert quantity to integer
            return {
                "name": pharmacy_name if pharmacy_name is not None else self.pharmacy_name,
                "mask_name": mask_name, 
                "mask_color": mask_color, 
                "pack_quantity": pack_quantity, 
                "price": mask_price
            }
        else:
            raise ValueError(f"Invalid mask format: {mask_string}")
        
    
    async def get_mask_info(self):
        """
        Parses and returns information for all masks in the `pharmacies_info[masks]`.
        """
        return [await self._parse_mask_info(mask_info) for mask_info in self.pharmacies_info["masks"]]
    

 
class ParseUserInfo(ParsePharmaciesInfo):
    def __init__(self, user_info: dict) -> None:
        self.user_info = user_info
        self.user_name = user_info.get("name")
        
    
    async def get_user_n_balance_info(self) -> dict:
        """ For the `users` table """
        return {
            "name": self.user_name,
            "cash_balance": self.user_info.get("cashBalance")
        }
        
    
    async def get_user_purchase_history(self) -> AsyncGenerator[dict, None]:
        """
        Generates the user's purchase history as a dictionary, yielding one record at a time.

        - Source: `self.user_info.get("purchaseHistories")`
        - Each record includes:
            - `user_id`: The username
            - `pharmacies`: The name of the pharmacy
            - `pharmacies_mask`: The dictionary containing mask information (name, color, pack quantity)
            - `trn_amount`: The transaction amount
            - `trn_date`: The transaction date (converted to `datetime` format)
        
        Yields:
            -  Generator[Dict[str, any], None, None]: Yields purchase history records one by one.

        Example:
        ```python
        
        user_info = ParseUserInfo(user_info)
        user_purchase_history = user_info.get_user_purchase_history()
        async for record in user_info.get_user_purchase_history:
            print(record)
            
        # the output will be like:
        {
            "user_id": "john_doe",
            "pharmacies": "ABC Pharmacy",
            "pharmacies_mask": {"N95 Mask", "color": "blue", "pack_quantity": 10},
            "trn_amount": 100,
            "trn_date": datetime(2021, 1, 4, 15, 18, 51)
        }...
        ```
        - If there are no purchase histories, it yields a dictionary with `None` values for `pharmacies`, `pharmacies_mask`, `trn_amount`, and `trn_date`.
        """
        from datetime import datetime
        user_purchase_histories = self.user_info.get("purchaseHistories")
        insert_table_schema = {
            "user_id": self.user_name,
            "pharmacies": None,
            "pharmacies_mask": None,
            "trn_amount": None,
            "trn_date": None
        }
        if len(user_purchase_histories) > 0:
            for purchase_history in user_purchase_histories:
                pharmacyName = purchase_history.get("pharmacyName")
                insert_table_schema["pharmacies"] = pharmacyName
                
                mask_info = await self._parse_mask_info(purchase_history.get("maskName"), pharmacy_name=pharmacyName)
                mask_info.pop('price')
                
                insert_table_schema["pharmacies_mask"] = mask_info
                insert_table_schema["trn_amount"] = purchase_history.get("transactionAmount")
                insert_table_schema["trn_date"] = datetime.strptime(purchase_history.get("transactionDate"), "%Y-%m-%d %H:%M:%S")
                
                yield insert_table_schema.copy()
        else:
            yield insert_table_schema



    
        
    
        
        
