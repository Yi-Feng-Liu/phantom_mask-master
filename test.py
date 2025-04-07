import psycopg2

# PostgreSQL 連線設定
conn = psycopg2.connect(
    host="10.88.26.119",
    port="5432",
    database="mydatabase",
    user="postgres",
    password="admin"
)

# 建立遊標
cursor = conn.cursor()

# 執行 SQL 查詢
cursor.execute("SELECT * FROM users_purchase_history")

# 獲取資料庫中的所有資料表
# cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")

# 獲取查詢結果
rows = cursor.fetchall()
for row in rows:
    print(row)

# 關閉連線和遊標
cursor.close()
conn.close()
