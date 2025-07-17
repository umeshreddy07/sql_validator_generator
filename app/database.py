# Import the PostgreSQL adapter for Python
import psycopg2
# Import Streamlit for accessing secrets and displaying messages
import streamlit as st

def get_db_connection():
    """Establishes and returns a database connection."""
    try:
        db_config = st.secrets.postgres
        return psycopg2.connect(
            host=db_config.host,
            port=db_config.port,
            user=db_config.user,
            password=db_config.password,
            dbname=db_config.dbname
        )
    except Exception as e:
        st.error(f"Failed to connect to the database: {e}")
        return None

def get_database_schema_string():
    """
    Connects to the PostgreSQL database and dynamically fetches the schema.
    Formats it into a SIMPLE string (table and column names only) 
    for the AI model.
    """
    conn = get_db_connection()
    if not conn:
        return "Error: Could not connect to the database to fetch schema."

    schema_string = ""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        for table in tables:
            table_name = table[0]
            schema_string += f"Table {table_name}, columns = ["
            cursor.execute(f"""
                SELECT column_name
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position;
            """)
            columns = cursor.fetchall()
            column_names = [col[0] for col in columns]
            schema_string += ", ".join(column_names) + "]\n"
        cursor.close()
        print("--- Dynamically Fetched Database Schema (Simplified for AI) ---")
        print(schema_string)
        print("----------------------------------------------------------------")
        return schema_string.strip()
    except psycopg2.Error as db_err:
        print(f"Database error while fetching schema: {db_err}")
        return f"Error: Database error while fetching schema: {db_err}"
    finally:
        if conn:
            conn.close()

def validate_sql_query(sql_query: str):
    """
    Validates the SQL query syntax using EXPLAIN without executing it.
    Returns (is_valid, message).
    """
    if not sql_query or not sql_query.strip():
        return False, "Query is empty."

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"EXPLAIN {sql_query}")
        cursor.close()
        return True, "Query syntax is valid."
    except psycopg2.Error as db_err:
        error_message = f"Invalid Query: {str(db_err).splitlines()[0]}"
        return False, error_message
    finally:
        if conn:
            conn.close()

def execute_pg_query(sql_query: str):
    """
    Executes a SQL query against the PostgreSQL database configured in Streamlit secrets.
    Returns a tuple: (results, error_message).
    'results' can be a list of dictionaries (for SELECT) or a success message string.
    'error_message' is a string if an error occurs, otherwise None.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql_query)
        results = None
        if sql_query.strip().upper().startswith("SELECT"):
            if cursor.description:
                colnames = [desc[0] for desc in cursor.description]
                results = [dict(zip(colnames, row)) for row in cursor.fetchall()]
            else:
                results = []
        else:
            conn.commit()
            results = f"Query executed successfully. Rows affected: {cursor.rowcount}"
        cursor.close()
        return results, None
    except psycopg2.Error as db_err:
        error_message = f"Database Execution Error: {str(db_err).splitlines()[0]}"
        return None, error_message
    finally:
        if conn:
            conn.close()

def list_tables():
    """
    Returns a list of all table names in the public schema.
    """
    conn = None
    try:
        db_config = {
            'host': st.secrets.postgres.host,
            'port': st.secrets.postgres.port,
            'user': st.secrets.postgres.user,
            'password': st.secrets.postgres.password,
            'dbname': st.secrets.postgres.dbname
        }
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE';
        """)
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return tables
    except Exception as e:
        print(f"Error listing tables: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_foreign_key_relationships():
    """
    Connects to the DB and fetches foreign key relationships.
    Returns a list of strings describing the relationships.
    """
    conn = get_db_connection()
    if not conn:
        return ["Error: Could not connect to DB for FKs."]
    relationships = []
    try:
        cursor = conn.cursor()
        query = """
        SELECT
            tc.table_name, 
            kcu.column_name, 
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name 
        FROM 
            information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
              AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY';
        """
        cursor.execute(query)
        for row in cursor.fetchall():
            table_name, column_name, foreign_table_name, foreign_column_name = row
            relationships.append(f"{table_name}.{column_name} can be joined with {foreign_table_name}.{foreign_column_name}")
        cursor.close()
        return relationships
    except psycopg2.Error as db_err:
        return [f"DB Error fetching FKs: {db_err}"]
    finally:
        if conn:
            conn.close() 