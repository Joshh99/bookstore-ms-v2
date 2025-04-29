import os
from sqlmodel import SQLModel, create_engine, Session, select, Field as SQLField
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")  # MySQL connection string
MONGO_URI = os.getenv("MONGO_URI")  # MongoDB connection string

# MySQL setup
engine = create_engine(DATABASE_URL)

# MongoDB setup
client = MongoClient(MONGO_URI)
db = client["bookstore"]
collection = db["books_<your-andrew-id>"]  # Replace <your-andrew-id> with your Andrew ID

# Database model for Book
class Book(SQLModel, table=True):
    ISBN: str = SQLField(primary_key=True)
    title: str = SQLField()
    Author: str = SQLField()
    description: str = SQLField()
    genre: str = SQLField()
    price: float = SQLField()
    quantity: int = SQLField()



def sync_books():
    try:
        # Read all books from MySQL
        with Session(engine) as session:
            books = session.exec(select(Book)).all()

        # Upsert each book into MongoDB
        for book in books:
            book_dict = {
                "ISBN": book.ISBN,
                "title": book.title,
                "Author": book.Author,
                "description": book.description,
                "genre": book.genre,
                "price": book.price,
                "quantity": book.quantity
            }
            collection.update_one(
                {"ISBN": book.ISBN},  # Query by ISBN
                {"$set": book_dict},  # Update or set these fields
                upsert=True  # Insert if not found
            )
        print("Book synchronization completed.")
    except Exception as e:
        print(f"Error during synchronization: {e}")


if __name__ == "__main__":
    sync_books()