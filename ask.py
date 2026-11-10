import os
import sqlite3
import pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai
import time


load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-flash-lite-latest")

# --- 1. Describe the database to the AI ---
# The AI can't see store.db, so we TELL it what the tables look like.
# This is called the "schema". Good text-to-SQL lives or dies on this.
SCHEMA = """
Tables in the database:

products(product_id, name, category, price)
customers(customer_id, name, region, signup_date)
orders(order_id, customer_id, product_id, quantity, discount, order_date)

Notes:
- order_date is text in 'YYYY-MM-DD' format.
- To get revenue for an order: price * quantity * (1 - discount).
- Join orders to products via product_id, and to customers via customer_id.
- Use strftime('%Y-%m', order_date) to group by month.
"""

# --- 2. Turn a question into SQL ---
def question_to_sql(question):
    prompt = f"""You are a SQL expert for a SQLite database.
{SCHEMA}

Write a single SQLite SQL query that answers this question:
"{question}"

Rules:
- Return ONLY the SQL query. No explanation, no markdown, no ``` fences.
- Use only the tables and columns listed above.
"""
    response = model.generate_content(prompt)
    sql = response.text.strip()
    # Sometimes the model wraps SQL in ```sql ... ``` anyway — strip that.
    sql = sql.replace("```sql", "").replace("```", "").strip()
    return sql

# --- 3. Run the SQL against our database ---
def run_sql(sql):
    conn = sqlite3.connect("store.db")
    result = pd.read_sql(sql, conn)
    conn.close()
    return result

# --- 4. Try it out ---
if __name__ == "__main__":
    question = "Which product category had the biggest revenue drop from May to June 2026?"

    print(f"Question: {question}\n")

    t0 = time.time()
    sql = question_to_sql(question)
    print(f"[SQL generated in {time.time() - t0:.1f}s]")

    print("Generated SQL:")
    print(sql)
    print()

    t1 = time.time()
    result = run_sql(sql)
    print(f"[SQL ran in {time.time() - t1:.1f}s]")

    print("Result:")
    print(result)