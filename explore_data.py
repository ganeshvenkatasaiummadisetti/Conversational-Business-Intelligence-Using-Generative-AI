import sqlite3
import pandas as pd

# Connect to the database we just built
conn = sqlite3.connect("store.db")

# pandas can run a SQL query and hand back a nice table (a "DataFrame")
print("=== First 5 products ===")
print(pd.read_sql("SELECT * FROM products LIMIT 5", conn))

print("\n=== First 5 orders ===")
print(pd.read_sql("SELECT * FROM orders LIMIT 5", conn))

# The important one: total revenue per month.
# revenue = price * quantity * (1 - discount), joined from orders -> products.
# strftime('%Y-%m', order_date) chops the date down to just year-month.
query = """
SELECT
    strftime('%Y-%m', o.order_date)              AS month,
    ROUND(SUM(p.price * o.quantity * (1 - o.discount)), 2) AS revenue,
    COUNT(*)                                      AS num_orders
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY month
ORDER BY month;
"""
print("\n=== Revenue by month ===")
print(pd.read_sql(query, conn))

conn.close()