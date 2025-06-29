import mysql.connector
from mysql.connector import Error

def stream_users():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="your_username",  # Replace with your MySQL username
            password="your_password",  # Replace with your MySQL password
            database="ALX_prodev"
        )
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM user_data")
        for row in cursor:
            yield row
    except Error as e:
        print(f"Error streaming users: {e}")
    finally:
        cursor.close()
        connection.close()