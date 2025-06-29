#!/usr/bin/python3
import seed
from typing import Dict, Generator, List

def paginate_users(page_size: int, offset: int) -> List[Dict[str, str|int]]:
    """
    Fetches a page of users from the database
    
    Args:
        page_size: Number of records per page
        offset: Starting position for the page
        
    Returns:
        list: A list of user dictionaries for the page
    """
    connection = seed.connect_to_prodev()
    cursor = connection.cursor(dictionary=True)
    cursor.execute(f"SELECT * FROM user_data LIMIT {page_size} OFFSET {offset}")
    rows = cursor.fetchall()
    connection.close()
    return rows

def lazy_paginate(page_size: int) -> Generator[List[Dict[str, str|int]], None, None]:
    """
    Generator function that lazily loads paginated user data
    
    Args:
        page_size: Number of records per page
        
    Yields:
        list: A page of user dictionaries
    """
    offset = 0
    while True:
        page = paginate_users(page_size, offset)
        if not page:
            break
        yield page
        offset += page_size

if __name__ == "__main__":
    import sys
    try:
        # Example usage: print users in pages of 100
        for page in lazy_paginate(100):
            for user in page:
                print(user)
    except BrokenPipeError:
        sys.stderr.close()