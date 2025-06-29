#!/usr/bin/python3
import mysql.connector
import sys
from typing import Dict, Generator, List

def stream_users_in_batches(batch_size: int) -> Generator[List[Dict[str, str|int]], None, None]:
    """
    Generator function that fetches users in batches from the database
    using only yield statements (no return)
    
    Args:
        batch_size: Number of records to fetch per batch
        
    Yields:
        list: A list of user dictionaries for each batch
    """
    connection = None
    cursor = None
    try:
        # Connect to the database
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="your_password",
            database="ALX_prodev"
        )
        
        # Use a server-side cursor for efficient batch fetching
        cursor = connection.cursor(dictionary=True)
        
        # Execute the query
        cursor.execute("SELECT * FROM user_data")
        
        # Fetch and yield rows in batches
        while True:
            batch = cursor.fetchmany(batch_size)
            if not batch:
                break
            yield batch
            
    except mysql.connector.Error as err:
        print(f"Database error: {err}", file=sys.stderr)
        yield []  # Yield empty list on error instead of returning
    finally:
        # Clean up resources
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def batch_processing(batch_size: int = 50) -> Generator[Dict[str, str|int], None, None]:
    """
    Processes users in batches and filters those over 25 years old
    using only yield statements (no return)
    
    Args:
        batch_size: Number of records to process per batch
        
    Yields:
        dict: Users over 25 years old one by one
    """
    # Get batch generator
    user_batches = stream_users_in_batches(batch_size)
    
    # Process and yield users over 25
    for batch in user_batches:
        for user in batch:
            if user['age'] > 25:
                yield user


if __name__ == "__main__":
    try:
        # Print processed users in batches of specified size
        user_generator = batch_processing(50)
        for user in user_generator:
            print(user)
    except BrokenPipeError:
        # Handle pipe closure gracefully
        sys.stderr.close()