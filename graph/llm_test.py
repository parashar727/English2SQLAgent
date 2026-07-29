import re

import ollama
from db.metadata import generate_markdown_schema
from db.session import query_database
import json
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg2://postgres:0727@localhost:5433/chinook"
engine = create_engine(DATABASE_URL)

print("Fetching database schema...")
dbschema = generate_markdown_schema(engine)

user_question = "What are top 5 most sold albums?"
print(f"User question: {user_question}")

system_prompt = f"""
You are an expert PostgreSQL developer. Your job is to convert natural language questions into valid SQL queries based ON ONLY the database schema provided below.

Rules:
1. Output ONLY the raw SQL query. Do not add markdown formatting or conversational text if possible.
2. Ensure column names match the schema exactly (PostgreSQL is case-sensitive for quoted identifiers if applicable).
3. Always include reasonable LIMITs (e.g., LIMIT 50) unless aggregating.

{dbschema}
"""

response = ollama.chat(
    model="qwen2.5-coder:1.5b",
    messages=[
        { "role": "system", "content": system_prompt },
        { "role": "user", "content": user_question }
    ]
    )


match = re.search(r"```(?:sql)?\s*(.*?)\s*```", response['message']['content'], re.DOTALL | re.IGNORECASE)
if match:
    print(match.group(1).replace("\n", " "))
    clean_sql_string = match.group(1).replace("\n", " ") # Look into if SQLAlchemy can just run with newlines anyway (so SQL comments dont break)
else:
    clean_sql_string = response['message']['content'].strip()

print(query_database(clean_sql_string))
