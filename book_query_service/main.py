from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import JSONResponse, Response, PlainTextResponse
import httpx
import time
import os
import json
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# Import database functions
from database import get_book_by_isbn, search_books_by_keyword, validate_keyword

# Circuit breaker configuration (reusing from A3)
RECOMMENDATION_URL = os.getenv("RECOMMENDATION_URL", "http://18.118.230.221/recommended-titles/isbn")
CIRCUIT_STATE_FILE = "/circuit_state/circuit.json"
TIMEOUT_SECONDS = 3
CIRCUIT_OPEN_SECONDS = 60

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

# Lifespan handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize circuit breaker state
    init_circuit_state()
    yield

# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)

# Status endpoint for liveness probe
@app.get("/status", status_code=status.HTTP_200_OK, response_class=PlainTextResponse)
async def get_status():
    return "OK"

# Endpoint to retrieve a book by ISBN
@app.get("/books/{ISBN}", status_code=status.HTTP_200_OK)
@app.get("/books/isbn/{ISBN}", status_code=status.HTTP_200_OK)
async def get_book(ISBN: str):
    book = get_book_by_isbn(ISBN)
    if not book:
        raise HTTPException(status_code=404, detail="ISBN not found")
    return JSONResponse(content=book)

# New endpoint: Search books by keyword
@app.get("/books", status_code=status.HTTP_200_OK)
async def search_books(keyword: str = Query(...)):
    try:
        if not validate_keyword(keyword):
            raise HTTPException(
                status_code=400, 
                detail="Keyword must contain only letters a-z and A-Z"
            )
        
        books = search_books_by_keyword(keyword)
        
        if not books:
            return Response(status_code=204)
        
        return JSONResponse(content=books)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Endpoint for related books (reusing circuit breaker from A3)
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
                if response.status_code == 200:
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