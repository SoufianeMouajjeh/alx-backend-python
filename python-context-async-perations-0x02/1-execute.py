import sqlite3

class ExecuteQuery:
    def __init__(self, database, query, params=None):
        self.database = database
        self.query = query
        self.params = params or []

    def __enter__(self):
        # Open the database connection and cursor
        self.connection = sqlite3.connect(self.database)
        self.cursor = self.connection.cursor()
        return self

    def execute(self):
        # Execute the provided query with parameters
        self.cursor.execute(self.query, self.params)
        return self.cursor.fetchall()

    def __exit__(self, exc_type, exc_value, traceback):
        # Close the cursor and connection
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()

# Usage example
if __name__ == "__main__":
    db_file = "user_info.db"  
    query = "SELECT * FROM users WHERE age > ?" 
    params = (25,)  

    with ExecuteQuery(db_file, query, params) as executor:
        results = executor.execute()
        for row in results:
            print(row)