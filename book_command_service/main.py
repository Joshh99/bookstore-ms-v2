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

# Circuit breaker configuration
RECOMMENDATION_URL = os.getenv("RECOMMENDATION_URL", "http://recommendation-service:8080/recommendations")
CIRCUIT_STATE_FILE = "/circuit_state/circuit.json"
TIMEOUT_SECONDS = 3
CIRCUIT_OPEN_SECONDS = 60

# Lifespan handler to manage startup and shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create database tables
    create_db_and_tables()
    yield
# Initialize FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

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

# Status endpoint
@app.get("/books/status", status_code=status.HTTP_200_OK, response_class=PlainTextResponse)
async def get_status():
    return "OK"

# Endpoint to add a book
@app.post("/books")
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
@app.put("/books/{ISBN}")
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



# Endpoint to retrieve a book by ISBN
@app.get("/books/{ISBN}", status_code=status.HTTP_200_OK)
@app.get("/books/isbn/{ISBN}", status_code=status.HTTP_200_OK)
async def get_book(ISBN: str):
    with Session(engine) as session:
        book = session.exec(select(Book).where(Book.ISBN == ISBN)).first()
        if not book:
            raise HTTPException(status_code=404, detail="ISBN not found")
        response = JSONResponse(content=dict(book))
        response.status_code = status.HTTP_200_OK
        return response



# Initialize circuit breaker state
def init_circuit_state():
    os.makedirs(os.path.dirname(CIRCUIT_STATE_FILE), exist_ok=True)
    if not os.path.exists(CIRCUIT_STATE_FILE):
        with open(CIRCUIT_STATE_FILE, "w") as f:
            json.dump({"state": "closed", "last_opened": 0}, f)

def get_circuit_state():
    try:
        with open(CIRCUIT_STATE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        init_circuit_state()
        return {"state": "closed", "last_opened": 0}

def set_circuit_state(state: str, last_opened: float = 0):
    with open(CIRCUIT_STATE_FILE, "w") as f:
        json.dump({"state": state, "last_opened": last_opened}, f)

@app.get("/books/{ISBN}/related-books")
async def get_related_books(ISBN: str):
    circuit = get_circuit_state()
    current_time = time.time()

    if circuit["state"] == "open":
        if current_time - circuit["last_opened"] < CIRCUIT_OPEN_SECONDS:
            raise HTTPException(status_code=503, detail="Service unavailable: circuit breaker open")
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                response = await client.get(f"{RECOMMENDATION_URL}/{ISBN}")
                if response.status_code == 200 :
                    books = response.json()
                    set_circuit_state("closed")
                    return JSONResponse(content=books, status_code=200)

                elif response.status_code == 204:
                    return Response(status_code=204)
                else:
                    set_circuit_state("open", current_time)
                    raise HTTPException(status_code=503, detail="Service unavailable")
        except (httpx.TimeoutException, httpx.RequestError):
            set_circuit_state("open", current_time)
            raise HTTPException(status_code=503, detail="Service timed out")

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.get(f"{RECOMMENDATION_URL}/{ISBN}")
            if response.status_code == 200:
                books = response.json()
                return JSONResponse(content=books, status_code=200) if books else JSONResponse(content={}, status_code=204)
            elif response.status_code == 204:
                return Response(status_code=204)
            else:
                raise HTTPException(status_code=503, detail="Service unavailable")
    except (httpx.TimeoutException, httpx.RequestError):
        set_circuit_state("open", current_time)
        raise HTTPException(status_code=504, detail="Service timed out")