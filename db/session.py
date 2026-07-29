from sqlalchemy import create_engine, text
import json

DATABASE_URL = "postgresql+psycopg2://postgres:0727@localhost:5433/chinook"
engine = create_engine(DATABASE_URL)

def query_database(sql_string, max_rows=50):
    """Query the database. Use this to send an SQL string to the database to be queried."""

    sql_statement = text(sql_string)

    try:
        with engine.connect() as conn:
            result = conn.execute(sql_statement)

            if not result.returns_rows:
                conn.commit()
                return json.dumps({
                    "status": "success",
                    "row_count": 0,
                    "data": "Query executed successfully. No rows returned"
                }, indent=2)

            # columns = list(result.keys())
            # rows = result.fetchmany(max_rows)

            # data = [dict(zip(columns, row)) for row in rows]

            rows = result.mappings().fetchmany(max_rows)

            data = [dict(row) for row in rows]

            payload = {
                "status": "success",
                "row_count": len(data) if data else 0,
                "data": "Query executed successfully, but returned 0 results." if not data else data
            }

            return json.dumps(payload, indent=2, default=str, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": str(e)
        }, indent=2)


if __name__ == "__main__":
    sql_statement = input("Enter the SQL statement: ")
    
    print(query_database(sql_statement))
        