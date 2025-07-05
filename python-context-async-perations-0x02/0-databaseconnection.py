import sqlite3

class DatabaseConnection:
    def __init__(self, database):
        self.database = database

    def __enter__(self):
        # Open the database connection
        self.connection = sqlite3.connect(self.database)
        return self.connection

    def __exit__(self, exc_type, exc_value, traceback):
        # Close the database connection
        if self.connection:
            self.connection.close()

# Usage example
if __name__ == "__main__":
    db_file = "user_info.db"  

    with DatabaseConnection(db_file) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users")
        results = cursor.fetchall()

        for row in results:
            print(row)