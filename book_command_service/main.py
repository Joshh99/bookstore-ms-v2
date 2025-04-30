from contextlib import asynccontextmanager  # Add for lifespan
from fastapi import FastAPI, HTTPException, status, Request, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse,Response, PlainTextResponse
from pydantic import BaseModel, constr, field_validator, Field, StrictInt, StrictFloat
from sqlalchemy.exc import IntegrityError
from database import Book, create_db_and_tables, engine, Session, select,APP_URL  # Import from database.py
from schemas import BookCreate
import httpx
import time
import os
import json


# Lifespan handler to manage startup and shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create database tables
    create_db_and_tables()
    yield
# Initialize FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

@app.get("/status")
async def status():
    return {"status": "ok"}

#custom exception handler to intercept HTTPExcetions
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
        headers=exc.headers,
    )


# Overwrite 422 error with 400
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"message": exc.errors()},
    )

# Handler for database integrity errors
@app.exception_handler(IntegrityError)
async def integrity_exception_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=400,
        content={"message": f"Database error: {str(exc.orig)}"}
    )

@app.get("/")
async def root():
    return {"message": "Hello World"}



# Endpoint to add a book
@app.post("/cmd/books")
async def add_book(book_data: BookCreate):
    with Session(engine) as session:
        book = Book(**dict(book_data))
        existing_book = session.exec(select(Book).where(Book.ISBN == book.ISBN)).first()
        if existing_book:
            raise HTTPException(status_code=422, detail="This ISBN already exists in the system.")
        session.add(book)
        session.commit()
        session.refresh(book)
        response = JSONResponse(content=dict(book))
        response.headers["Location"] = f"{APP_URL}/books/{book.ISBN}"
        response.status_code = status.HTTP_201_CREATED
        return response

# Endpoint to update a book
@app.put("/cmd/books/{ISBN}")
async def update_book(ISBN: str, book: BookCreate):
    if book.__pydantic_fields_set__.__len__() != book.model_fields.__len__():
        raise HTTPException(status_code=400, detail="Invalid request body.")
    with Session(engine) as session:
        if ISBN != book.ISBN:
            raise HTTPException(status_code=400, detail="The ISBN in the path and body do not match.")
        db_book = session.exec(select(Book).where(Book.ISBN == ISBN)).first()
        if not db_book:
            raise HTTPException(status_code=404, detail="ISBN not found")
        for key, value in dict(book).items():
            setattr(db_book, key, value)
        session.add(db_book)
        session.commit()
        session.refresh(db_book)
        response = JSONResponse(content=dict(db_book))
        response.status_code = status.HTTP_200_OK
        return response








