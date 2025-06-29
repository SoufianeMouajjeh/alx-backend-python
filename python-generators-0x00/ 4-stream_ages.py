import mysql.connector
from mysql.connector import Error

def stream_user_ages():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="your_username",  # Replace with your MySQL username
            password="your_password",  # Replace with your MySQL password
            database="ALX_prodev"
        )
        cursor = connection.cursor()
        cursor.execute("SELECT age FROM user_data")
        for (age,) in cursor:
            yield float(age)
    except Error as e:
        print(f"Error streaming ages: {e}")
    finally:
        cursor.close()
        connection.close()

def calculate_average_age():
    total_age = 0
    count = 0
    for age in stream_user_ages():
        total_age += age
        count += 1
    average_age = total_age / count if count > 0 else 0
    print(f"Average age of users: {average_age:.2f}")

if __name__ == "__main__":
    calculate_average_age()