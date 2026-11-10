<div align="center">

# 📊 Conversational Business Intelligence Using Generative AI

### Ask a business question in plain English — get SQL, real data, a chart, and an executive insight, instantly.

An LLM-powered analytics agent that turns natural-language questions into SQL, runs them against a live database, recovers from its own errors, and explains the results the way a human analyst would.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Gemini](https://img.shields.io/badge/Google_Gemini-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)

**Built by Ishant Yadav**

</div>

---

## 💡 The Problem

Executives don't want dashboards — they want answers. Getting one usually means waiting on an analyst to write SQL, pull the data, build a chart, and interpret it.

**This tool collapses that entire loop into a single question.** Ask *"Why did revenue drop last month?"* in plain English, and in seconds you get the SQL, the data, a chart, and a written executive insight with a recommended action.

---

## 🎥 See it in action

**Ask a question → get an answer explained like an analyst would:**

![Revenue drop analysis with AI insight](demo-insight.png)

The agent pinpoints the exact category behind a revenue drop and explains the likely cause — then recommends an action.

**Every result is visualized automatically:**

![Revenue by region with chart](demo-chart.png)

**The agent writes its own SQL — and fixes itself when a query fails:**

![Self-correcting retry loop](demo-selfcorrecting.png)

When a query errors, the agent feeds the database error back to the model and retries — correcting itself instead of crashing.

**Point it at *your* data — upload any CSV or Excel file:**

![Upload your own data](demo-upload.png)

Column names are auto-cleaned so the AI can query arbitrary datasets, not just the built-in demo.

---

## ⚡ Key Features

| Feature | What it does |
|---------|-------------|
| 🧠 **Natural-language → SQL** | Generates correct SQL from a plain-English question using only a schema description |
| 🔄 **Self-correcting agent** | Reads its own database errors and retries up to 3 times before giving up gracefully |
| 📝 **Executive insights** | A second AI pass explains findings in business language and suggests actions |
| 📊 **Interactive result views** | Review result metrics and data, then choose the chart axes and visualization type |
| 🔎 **Data explorer** | Inspect table sizes, field types, primary keys, and row previews; generate an AI overview |
| 📁 **Bring your own data** | Upload any CSV/Excel file; schema is detected and cleaned automatically |
| 🕘 **Query history & CSV export** | Re-run past questions and download results |

---

## 🧠 How it works

```
User question
     │
     ▼
Generate SQL  ◄─────────────┐
     │                      │  (on error: feed the
     ▼                      │   error back and retry)
Run against database ───────┘
     │
     ▼
Return data  ──►  AI writes an executive insight
     │
     ▼
Auto-generate a chart
```

The design separates **decisions** (made by the LLM) from **actions** (executed by reliable Python code): the model writes and fixes SQL and interprets results, while the code validates and runs everything. This "trust but verify" architecture is what makes it robust rather than a thin prompt wrapper.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python |
| LLM | Google Gemini (`gemini-flash-lite-latest`) |
| Database | SQLite |
| Data handling | pandas, SQLAlchemy |
| Web UI | Streamlit |
| Charts | matplotlib |

---

## 🚀 Run it yourself

```bash
# 1. Clone
git clone https://github.com/ishant2034/AI-Business-Analyst.git
cd AI-Business-Analyst

# 2. Virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Build the demo database
python create_database.py

# 5. Run the app
streamlit run app.py
```

**API key:** Get a free key from [Google AI Studio](https://aistudio.google.com/apikey) (no credit card needed), then create a `.env` file in the project root:
```
GEMINI_API_KEY=your_key_here
```

The app opens at `http://localhost:8501`.

---

## 💬 Example questions

- *What is the total revenue for each month?*
- *Which product category had the biggest revenue drop from May to June 2026?*
- *How much revenue came from each region?*
- *Who are the top 5 customers by spending?*

---

## 🔒 Notes

- Runs entirely on Google Gemini's **free tier** — no paid API required.
- Only a small sample of uploaded data is sent to the LLM to generate queries. Avoid uploading sensitive data on the free tier.
- A command-line version is also included — run `python agent.py` for an interactive terminal experience.

---

<div align="center">

*Built as a portfolio project demonstrating LLM agents, text-to-SQL, and AI-powered data analytics.*

</div>
