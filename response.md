# Response
> The Current content is an **example template**; please edit it to fit your style and content.
## A. Required Information
### A.1. Requirement Completion Rate
- [x] List all pharmacies open at a specific time and on a day of the week if requested.
  - Implemented at Fast API.
- [x] List all masks sold by a given pharmacy, sorted by mask name or price.
  - Implemented at Fast API.
- [x] List all pharmacies with more or less than x mask products within a price range.
  - Implemented at Fast API.
- [x] The top x users by total transaction amount of masks within a date range.
  - Implemented at Fast API.
- [x] The total number of masks and dollar value of transactions within a date range.
  - Implemented at Fast API.
- [x] Search for pharmacies or masks by name, ranked by relevance to the search term.
  - Implemented at Fast API.
- [x] Process a user purchases a mask from a pharmacy, and handle all relevant data changes in an atomic transaction.
  - Implemented at Fast API. (The purchase_mask API still has some bugs that need to be fixed)
### A.2. API Document
> Please describe how to use the API in the API documentation. [hackMD](https://hackmd.io/@cwF9ispYTA-KUFDkXo-sLQ/B1-1fdb0yl).


### A.3. Import Data Commands
After setting up `PostgreSQL`, modify the PostgreSQL configuration in `lines 145-150` of the `save_data_to_db.py` file. 
Once that's done, simply execute the script, and it will perform the ETL process on the JSON files in the data directory and write the data into the database.

## B. Other Information

### B.1. ERD

My ERD [erd-link](https://dbdiagram.io/d/KD-System-ERD-YF-67ee530c4f7afba1843478f5).

### B.2. Technical Document

For frontend programmer reading, please check this [technical document](https://hackmd.io/@cwF9ispYTA-KUFDkXo-sLQ/rkBXM_-Cye) to know how to operate those APIs.
- --
