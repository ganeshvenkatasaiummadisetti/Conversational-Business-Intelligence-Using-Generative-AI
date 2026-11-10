import os
import sqlite3
import time
import json
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-flash-lite-latest")

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


def build_schema_from_db(db_path):
    """Inspect any SQLite database and auto-generate a schema description."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    lines = ["Tables in the database:\n"]
    for table in tables:
        cursor.execute(f'PRAGMA table_info("{table}")')
        cols = [row[1] for row in cursor.fetchall()]  # row[1] is the column name
        lines.append(f'"{table}"({", ".join(cols)})')

    conn.close()
    return "\n".join(lines)


def clean_sql(text):
    """Strip markdown fences the model sometimes adds."""
    return text.replace("```sql", "").replace("```", "").strip()


def generate_sql(question, error_context=None, schema=SCHEMA):
    """Ask Gemini for SQL. If error_context is given, it's a RETRY:
    we include the previous broken SQL and the error so it can fix itself."""
    if error_context is None:
        prompt = f"""You are a SQL expert for a SQLite database.
{schema}

Write a single SQLite SQL query that answers this question:
"{question}"

Rules:
- Return ONLY the SQL query. No explanation, no markdown, no ``` fences.
- Use only the tables and columns listed above.
"""
    else:
        prompt = f"""You are a SQL expert for a SQLite database.
{schema}

Your previous query for the question "{question}" FAILED.

The broken SQL was:
{error_context['sql']}

The database returned this error:
{error_context['error']}

Fix the query. Return ONLY the corrected SQLite SQL query, no markdown, no explanation.
Use only the tables and columns listed in the schema above.
"""
    response = model.generate_content(prompt)
    return clean_sql(response.text)


def run_sql(sql, db_path="store.db"):
    """Run SQL and return a DataFrame. Raises an exception if the SQL is bad."""
    conn = sqlite3.connect(db_path)
    try:
        return pd.read_sql(sql, conn)
    finally:
        conn.close()

def describe_table(table_name, db_path):
    """Explain what's inside a table in plain English — no SQL question needed."""
    conn = sqlite3.connect(db_path)
    # Grab a sample and basic info
    sample = pd.read_sql(f'SELECT * FROM "{table_name}" LIMIT 15', conn)
    row_count = pd.read_sql(f'SELECT COUNT(*) AS n FROM "{table_name}"', conn)["n"][0]
    conn.close()

    columns = list(sample.columns)
    sample_text = sample.to_string(index=False)

    prompt = f"""You are a data analyst helping a colleague understand a new dataset.

Table name: "{table_name}"
Total rows: {row_count}
Columns: {columns}

Here is a sample of the data:
{sample_text}

Write a clear, friendly overview (4-6 sentences) covering:
- What this dataset appears to be about
- What the key columns represent
- Any obvious patterns, categories, or things worth noting
- What kinds of questions someone could ask about it

Talk in plain business English. Do not write any SQL."""
    response = model.generate_content(prompt)
    return response.text.strip()
def describe_table(table_name, db_path):
    """Explain what's inside a table in plain English — no SQL question needed."""
    conn = sqlite3.connect(db_path)
    sample = pd.read_sql(f'SELECT * FROM "{table_name}" LIMIT 15', conn)
    row_count = pd.read_sql(f'SELECT COUNT(*) AS n FROM "{table_name}"', conn)["n"][0]
    conn.close()

    columns = list(sample.columns)
    sample_text = sample.to_string(index=False)

    prompt = f"""You are a data analyst helping a colleague understand a new dataset.

Table name: "{table_name}"
Total rows: {row_count}
Columns: {columns}

Here is a sample of the data:
{sample_text}

Write a clear, friendly overview (4-6 sentences) covering:
- What this dataset appears to be about
- What the key columns represent
- Any obvious patterns, categories, or things worth noting
- What kinds of questions someone could ask about it

Talk in plain business English. Do not write any SQL."""
    response = model.generate_content(prompt)
    return response.text.strip()
def explain_result(question, sql, result_df):
    """Second AI call: interpret the data in plain business English."""
    data_text = result_df.to_string(index=False)

    prompt = f"""You are a business analyst presenting to an executive.

The user asked: "{question}"

This SQL was run:
{sql}

It returned this data:
{data_text}

Write a short, clear business insight (3-5 sentences):
- State the key finding in plain English (no jargon).
- Point out anything notable (a spike, a drop, a leader, an outlier).
- If relevant, suggest one action the business could take.
Do not describe the SQL or the table format. Talk about the business.
"""
    response = model.generate_content(prompt)
    return response.text.strip()


def make_chart(question, result_df):
    """Ask the AI what chart fits the data, then render it with matplotlib."""
    if result_df.shape[0] < 2 or result_df.shape[1] < 2:
        print("(Not enough data to chart — skipping.)")
        return

    columns = list(result_df.columns)
    data_preview = result_df.head(10).to_string(index=False)

    prompt = f"""You are a data visualization expert.

The user asked: "{question}"
The result has these columns: {columns}
Here is a preview of the data:
{data_preview}

Decide the best chart. Reply with ONLY a JSON object, no markdown, in this exact form:
{{"chart_type": "bar" or "line" or "pie", "x": "<column for x-axis/labels>", "y": "<column for values>", "title": "<a short chart title>"}}
"""
    response = model.generate_content(prompt)
    raw = response.text.replace("```json", "").replace("```", "").strip()

    try:
        spec = json.loads(raw)
    except json.JSONDecodeError:
        print(f"(Could not read chart spec from AI: {raw})")
        return

    x_col = spec.get("x")
    y_col = spec.get("y")
    chart_type = spec.get("chart_type", "bar")
    title = spec.get("title", question)

    if x_col not in result_df.columns or y_col not in result_df.columns:
        print(f"(AI picked columns that don't exist: {x_col}, {y_col} — skipping chart.)")
        return

    print(f"(AI chose a {chart_type} chart: {x_col} vs {y_col})")

    plt.figure(figsize=(9, 5))
    if chart_type == "line":
        plt.plot(result_df[x_col], result_df[y_col], marker="o")
    elif chart_type == "pie":
        plt.pie(result_df[y_col], labels=result_df[x_col].astype(str), autopct="%1.1f%%")
    else:
        plt.bar(result_df[x_col].astype(str), result_df[y_col])

    plt.title(title)
    if chart_type != "pie":
        plt.xlabel(x_col)
        plt.ylabel(y_col)
        plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.show()


def ask_agent(question, max_attempts=3, schema=SCHEMA, db_path="store.db"):
    """The agent loop: generate, run, and self-correct on failure."""
    error_context = None

    for attempt in range(1, max_attempts + 1):
        print(f"\n--- Attempt {attempt} ---")

        sql = generate_sql(question, error_context, schema)
        print("Generated SQL:")
        print(sql)

        try:
            result = run_sql(sql, db_path)
            print(f"\n✅ Success on attempt {attempt}!")
            return result, sql
        except Exception as e:
            print(f"\n❌ Error: {e}")
            error_context = {"sql": sql, "error": str(e)}

    print(f"\n⚠️ Gave up after {max_attempts} attempts.")
    return None, None


if __name__ == "__main__":
    print("=" * 55)
    print("  AI Business Analyst  —  ask me about your store data")
    print("  Type your question, or type 'quit' to exit.")
    print("=" * 55)

    while True:
        question = input("\n💬 Your question: ").strip()

        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        if not question:
            continue

        result, sql = ask_agent(question)

        if result is None:
            print("Sorry, I couldn't answer that one. Try rephrasing.")
            continue

        print("\n=== Data ===")
        print(result)

        print("\n=== AI Insight ===")
        insight = explain_result(question, sql, result)
        print(insight)

        print("\n=== Chart ===")
        make_chart(question, result)