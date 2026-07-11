from sqlalchemy import create_engine, inspect

DATABASE_URL = "postgresql+psycopg2://postgres:0727@localhost:5433/chinook"
engine = create_engine(DATABASE_URL)

def generate_markdown_schema(engine):
    inspector = inspect(engine)

    tables = inspector.get_table_names(schema="public")

    markdown_schema = ["## Database Schema Blueprint\n"]

    for table in tables:
        markdown_schema.append(f"\n### Table: '{table}'")
        markdown_schema.append(f"#### **Columns:**")

        columns = inspector.get_columns(table_name=table)
        pks = inspector.get_pk_constraint(table_name=table) #primary keys
        fks = inspector.get_foreign_keys(table_name=table) #foreign keys
        fk_map = {} #making a lookup table for foreign keys
        for fk in fks:
            fk_map[fk['constrained_columns'][0]] = f"{fk['referred_table']}.{fk['referred_columns'][0]}"

        
        for column in columns:
            if column['name'] in pks['constrained_columns']:
                markdown_schema.append(f"* '{column['name']}' ({column['type']}) [PRIMARY KEY]")
            elif column['name'] in fk_map.keys():
                markdown_schema.append(f"* '{column['name']}' ({column['type']}) [FOREIGN KEY -> {fk_map[column['name']]}]")
            else:
                markdown_schema.append(f"* '{column['name']}' ({column['type']})")
            

        
        # print(columns)
        # print(pks)
        # print(fks)


    return "\n".join(markdown_schema)


if __name__ == "__main__":
        inspector = inspect(engine)

        tables = inspector.get_table_names(schema="public")
        print(f"Tables: {tables}")

        schema = generate_markdown_schema(engine)
        print(schema)