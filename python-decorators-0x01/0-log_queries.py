import sqlite3
import functools
from datetime import datetime

def log_queries(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        query = args[0]  # The query is the first positional argument
        print(f"Executing query: {query}")
        result = func(*args, **kwargs)
        end_time = datetime.now()
        execution_time = end_time - start_time
        print(f"Query completed in {execution_time.total_seconds():.4f} seconds")
        return result
    return wrapper

@log_queries
def fetch_all_users(query):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    return results

# Example usage
if __name__ == "__main__":
    users = fetch_all_users(query="SELECT * FROM users")
    print(users)