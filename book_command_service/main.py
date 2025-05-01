from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.exc import IntegrityError
from database import Book, create_db_and_tables, engine, Session, select, APP_URL
from schemas import BookCreate
import os

# Lifespan handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables
    create_db_and_tables()
    yield

# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)

# Exception handlers
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
        headers=exc.headers,
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"message": exc.errors()},
    )

@app.exception_handler(IntegrityError)
async def integrity_exception_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=400,
        content={"message": f"Database error: {str(exc.orig)}"}
    )

# Status endpoint for liveness probe
@app.get("/status", status_code=status.HTTP_200_OK, response_class=PlainTextResponse)
async def get_status():
    return "OK"

# Command endpoints with /cmd/ path prefix
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