from langchain.tools import tool
import datetime
import pyodbc
import sys
from os import getenv
from dotenv import load_dotenv


@tool
def get_current_time():
    """Returns the current time in a human-readable format."""
    return datetime.datetime.now().strftime("%H:%M:%S")


@tool
def say_hello(name: str):
    """Says hello to a person given their name."""
    return f"Hello, {name}!"

@tool
def transfer_table_data(query: str) -> str:
    """Transfers a full table from one SQL database to another.

    Input format: 'transfer [schema].[table] from [source_db] to [dest_db]'
    Example: 'transfer dbo.DB_EVENTS from dw_production to TempObjDB'

    Args:
        query: A string describing the transfer operation
    """
    try:
        import re

        # Parse the input string
        # Pattern: transfer [schema].[table] from [source_db] to [dest_db]
        pattern = r'transfer\s+(?:(\w+)\.)?(\w+)\s+from\s+(\w+)\s+to\s+(\w+)'
        match = re.search(pattern, query.lower())

        if not match:
            return "Error: Could not parse the transfer command. Use format: 'transfer [schema].[table] from [source_db] to [dest_db]'"

        source_schema = match.group(1) or 'dbo'
        source_table = match.group(2)
        source_database = match.group(3)
        destination_database = match.group(4)
        destination_schema = 'dbo'
        destination_table = source_table

        # Your existing transfer logic
        load_dotenv()
        driver = getenv("SQL_DRIVER")
        server = getenv("SQL_SERVER")

        conn_str = (
            f"DRIVER={driver};"
            f"SERVER={server};"
            f"DATABASE={source_database};"
            f"Trusted_Connection=yes;"
            f"Encrypt=yes;"
            f"TrustServerCertificate=yes;"
        )

        db_conn = pyodbc.connect(conn_str)
        cursor = db_conn.cursor()

        source_full_name = f"[{source_schema}].[{source_table}]"
        target_full_name = f"[{destination_database}].[{destination_schema}].[{destination_table}]"

        # Check if the table already exists in the target database
        check_table_sql = f"IF OBJECT_ID(N'{target_full_name}', 'U') IS NOT NULL SELECT 1 ELSE SELECT 0;"
        cursor.execute(check_table_sql)
        if cursor.fetchone()[0] == 1:
            return f"Error: The target table already exists in '{destination_database}'."

        transfer_sql = f"SELECT * INTO {target_full_name} FROM {source_full_name};"
        print("Executing data transfer query...")
        cursor.execute(transfer_sql)
        db_conn.commit()
        print("Data transfer successful!")

        return f"Table transfer completed successfully: {source_full_name} from {source_database} to {target_full_name}"

    except pyodbc.Error as ex:
        return f"An error occurred during data transfer: {ex}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"
    finally:
        if 'db_conn' in locals() and db_conn:
            db_conn.close()