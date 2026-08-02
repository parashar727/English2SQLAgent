from typing import Literal, TypedDict, List, Annotated
import operator
import re
import json
from sqlalchemy import create_engine, text

from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from db.metadata import generate_markdown_schema
from db.session import query_database

class AgentState(TypedDict):
    user_query: str
    dbschema: str
    generated_sql: str
    sql_result: dict
    sql_result_summary: str
    retry_count: int
    messages: Annotated[List[BaseMessage], operator.add]

model = ChatOllama(model="qwen2.5-coder:3b", num_gpu=1, temperature=0.1) # Look into if SQL generation and SQL summaries can use different models

def generate_sql_node(state: AgentState):
    system_prompt = f"""
    You are an expert PostgreSQL developer. Your job is to convert natural language questions into valid SQL queries based ON ONLY the database schema provided below.

    Rules:
    1. Output ONLY the raw SQL query. Do not add markdown formatting or conversational text if possible.
    2. Ensure column names match the schema exactly (PostgreSQL is case-sensitive for quoted identifiers if applicable).
    3. Always include reasonable LIMITs (e.g., LIMIT 50) unless aggregating.

    {state.get("dbschema")}
    """
    sql_result = state.get("sql_result")
    if sql_result and sql_result.get("status") == "error":
        state["retry_count"] = state.get("retry_count", 0) + 1
        response = model.invoke(
                    [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=state.get("user_query"))
                    ]
                    + [HumanMessage(content=f"Your previous SQL query failed with the error: {sql_result.get("error_message")}. Please fix the query.")]
                )
    else:
        response = model.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=state.get("user_query"))
            ]
        )

    match = re.search(r"```(?:sql)?\s*(.*?)\s*```", response.content, re.DOTALL | re.IGNORECASE)
    if match:
        print(match.group(1).replace("\n", " "))
        clean_sql_string = match.group(1).strip()
    else:
        clean_sql_string = response.content.strip()

    return {
        "messages": [response],
        "generated_sql": clean_sql_string,
    }

def execute_sql_node(state: AgentState):
    sql_return = json.loads(query_database(state["generated_sql"]))
    print(sql_return)

    return {
        "sql_result": sql_return,
    }

def format_response_node(state: AgentState):
    system_prompt = f"""
    You are an expert data analyst. Your job is to analyze and write a short answer that summarizes the findings using the original User Question and the returned SQL Query result from the database.

    [INSTRUCTIONS]
    Provide a concise summary of this data by following these strict rules:
    1. Executive Summary: Give a 1-2 sentence overview of the main takeaway.
    2. Key Metrics & Trends: Identify the highest values, lowest values, and notable patterns. 
    3. Anomalies: Point out any outliers, missing data, or unexpected drops/spikes.
    4. Actionable Insight: Suggest 1-2 logical next steps based on these findings.

    [CONSTRAINTS]
    - Strict Accuracy: Rely ONLY on the provided data. Do not invent or extrapolate numbers.
    - Formatting: Use bullet points and bold text for key figures.
    - If the data is insufficient to draw a conclusion, explicitly state what is missing.

    User Question: {state.get("user_query")}

    Returned rows: {state.get("sql_result").get("data")}
    """

    response = model.invoke(
        [SystemMessage(content=system_prompt)]
    )

    return {
        "messages": [response],
        "sql_result_summary": response.content
    }

MAX_RETRIES = 3

def decide_next(state: AgentState) -> Literal["generate_sql", "format_response", END]: # type: ignore
    """Inspect generated SQL to decide where to go next."""
    if state.get("sql_result").get("status") == "error":
        if state.get("retry_count") >= MAX_RETRIES:
            print("Model cannot construct a working query, please use a better model.")
            return END
        else: 
            return "generate_sql"
    else:
        return "format_response"

#Building workflow
workflow = StateGraph(AgentState)

#Nodes
workflow.add_node("generate_sql", generate_sql_node)
workflow.add_node("execute_sql", execute_sql_node)
workflow.add_node("format_response", format_response_node)

#edges
workflow.add_edge(START, "generate_sql")
workflow.add_edge("generate_sql", "execute_sql")

#Conditional edge
workflow.add_conditional_edges("execute_sql", decide_next, {"generate_sql": "generate_sql", "format_response": "format_response"},)

workflow.add_edge("format_response", END)

graph = workflow.compile()

DATABASE_URL = "postgresql+psycopg2://postgres:0727@localhost:5433/chinook"
engine = create_engine(DATABASE_URL)

database_schema = generate_markdown_schema(engine)

inital_state = {
    "user_query": "What are the top 5 most spending customers?",
    "dbschema": database_schema,
    "retry_count": 0,
}

response = graph.invoke(inital_state)

for msg in response["messages"]:
    msg.pretty_print()