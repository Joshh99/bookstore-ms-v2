import os
import re
from typing import List, Optional, Dict, Any
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection settings
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "bookstore")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "books")

if not MONGO_URI:
    raise ValueError("MONGO_URI is not set in the environment or .env file")

# MongoDB client setup
client = MongoClient(MONGO_URI)
db: Database = client[MONGO_DB]
books_collection: Collection = db[MONGO_COLLECTION]

# Ensure text index is created for full-text search
# This creates a text index on title, Author, description, and genre fields
books_collection.create_index([
    ("title", "text"), 
    ("Author", "text"), 
    ("description", "text"), 
    ("genre", "text")
])

# Book model (for type hints and structure)
class Book(BaseModel):
    ISBN: str
    title: str
    Author: str
    description: str
    genre: str
    price: float
    quantity: int

# Database query functions
def get_book_by_isbn(isbn: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a book document from MongoDB by ISBN.
    
    Args:
        isbn: The ISBN of the book to retrieve
        
    Returns:
        Book document as a dictionary or None if not found
    """
    return books_collection.find_one({"ISBN": isbn}, {"_id": 0})

def search_books_by_keyword(keyword: str) -> List[Dict[str, Any]]:
    """
    Search for books containing the specified keyword in any indexed field.
    
    Args:
        keyword: The search keyword
        
    Returns:
        List of matching book documents as dictionaries
    """
    if not validate_keyword(keyword):
        raise ValueError("Keyword must contain only letters a-z and A-Z")
    
    # Use text search for the keyword
    # The $text operator uses the text index created above
    query = {"$text": {"$search": keyword}}
    
    # Exclude _id field from results and sort by relevance score
    results = books_collection.find(
        query, 
        {"_id": 0, "score": {"$meta": "textScore"}}
    ).sort([("score", {"$meta": "textScore"})])
    
    return list(results)

def validate_keyword(keyword: str) -> bool:
    """
    Validate that the keyword contains only letters a-z and A-Z.
    
    Args:
        keyword: The keyword to validate
        
    Returns:
        True if the keyword is valid, False otherwise
    """
    return bool(re.match(r'^[a-zA-Z]+$', keyword))