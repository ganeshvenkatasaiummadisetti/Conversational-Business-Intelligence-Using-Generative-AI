import sqlite3
import random
from datetime import datetime, timedelta

# random.seed makes the "random" data the same every time we run this.
# That means your results are reproducible — important for debugging.
random.seed(42)

# Connect to a database file. If store.db doesn't exist, SQLite creates it.
conn = sqlite3.connect("store.db")
cursor = conn.cursor()

# --- 1. Define the schema (create the tables) ---
# We drop old tables first so re-running this script always gives a clean start.
cursor.executescript("""
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

CREATE TABLE products (
    product_id   INTEGER PRIMARY KEY,
    name         TEXT,
    category     TEXT,
    price        REAL
);

CREATE TABLE customers (
    customer_id  INTEGER PRIMARY KEY,
    name         TEXT,
    region       TEXT,
    signup_date  TEXT
);

CREATE TABLE orders (
    order_id     INTEGER PRIMARY KEY,
    customer_id  INTEGER,
    product_id   INTEGER,
    quantity     INTEGER,
    discount     REAL,
    order_date   TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (product_id)  REFERENCES products(product_id)
);
""")

# --- 2. Insert products ---
products = [
    (1, "Wireless Earbuds",   "Audio",       59.99),
    (2, "Noise-Cancel Headphones", "Audio",  199.99),
    (3, "4K Monitor",         "Displays",    329.99),
    (4, "Ultrawide Monitor",  "Displays",    549.99),
    (5, "Mechanical Keyboard","Accessories",  89.99),
    (6, "Wireless Mouse",     "Accessories",  39.99),
    (7, "Laptop Stand",       "Accessories",  34.99),
    (8, "Webcam 1080p",       "Accessories",  69.99),
]
cursor.executemany(
    "INSERT INTO products VALUES (?, ?, ?, ?)", products
)

# --- 3. Insert customers ---
regions = ["North", "South", "East", "West"]
customers = []
for cid in range(1, 201):  # 200 customers
    name = f"Customer {cid}"
    region = random.choice(regions)
    # Signed up sometime in the last ~2 years
    signup = datetime(2024, 1, 1) + timedelta(days=random.randint(0, 700))
    customers.append((cid, name, region, signup.strftime("%Y-%m-%d")))
cursor.executemany(
    "INSERT INTO customers VALUES (?, ?, ?, ?)", customers
)

# --- 4. Insert orders — this is where we hide the "story" ---
# We generate orders across 6 months. In the LAST month, we make the
# "Displays" category collapse (supplier issue) so revenue drops.
orders = []
order_id = 1
start = datetime(2026, 1, 1)

for month_offset in range(6):  # 6 months of data
    month_start = start + timedelta(days=30 * month_offset)
    is_last_month = (month_offset == 5)

    for _ in range(300):  # ~300 orders per month
        customer_id = random.randint(1, 200)
        product_id = random.randint(1, 8)

        # THE HIDDEN STORY: in the last month, Displays (products 3 & 4)
        # almost stop selling — simulate a supply shortage.
        if is_last_month and product_id in (3, 4):
            if random.random() < 0.85:      # 85% chance we skip this order
                continue

        quantity = random.randint(1, 3)
        discount = random.choice([0, 0, 0, 0.1, 0.2])  # most orders no discount
        day = random.randint(0, 29)
        order_date = (month_start + timedelta(days=day)).strftime("%Y-%m-%d")

        orders.append((order_id, customer_id, product_id,
                       quantity, discount, order_date))
        order_id += 1

cursor.executemany(
    "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)", orders
)

# --- 5. Save and close ---
conn.commit()
conn.close()

print(f"Database created: store.db")
print(f"Inserted {len(products)} products, {len(customers)} customers, {len(orders)} orders.")