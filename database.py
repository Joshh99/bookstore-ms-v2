import os
from sqlmodel import Field as SQLField, SQLModel, create_engine, Session, select
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from file
load_dotenv()

# Get app_url
APP_URL = os.getenv("APP_URL")

# Get DATABASE_URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in the environment or .env file")

# Database connection
Is_debugging = os.getenv("IS_DEBUGGING") == 'true'
engine = create_engine(DATABASE_URL, echo=Is_debugging)  # echo=True for debugging

# Database model for Book
class Book(SQLModel, table=True):
    ISBN: str = SQLField(primary_key=True)
    title: str = SQLField()
    Author: str = SQLField()
    description: str = SQLField()
    genre: str = SQLField()
    price: float = SQLField()
    quantity: int = SQLField()

# Database model for Customer
class Customer(SQLModel, table=True):
    id: Optional[int] = SQLField(default=None, primary_key=True)
    userId: str = SQLField()
    name: str = SQLField()
    phone: str = SQLField()
    address: str = SQLField()
    address2: Optional[str] = SQLField(default=None)
    city: str = SQLField()
    state: str = SQLField()
    zipcode: str = SQLField()

# Create tables on startup
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# Database utility functions (optional, can expand later)
def get_session():
    with Session(engine) as session:
        yield session