from fastapi import FastAPI, HTTPException, Request, Query  
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse, JSONResponse, Response
import httpx
import os
from dotenv import load_dotenv
from utils import validate_jwt
from schemas import BookCreate, BookResponse, CustomerCreate, CustomerResponse

app = FastAPI()
# Load environment variables from file
load_dotenv()

# Updated URL environment variables
CUSTOMER_URL = os.getenv("CUSTOMER_URL")
BOOK_COMMAND_URL = os.getenv("BOOK_COMMAND_URL")  # For write operations
BOOK_QUERY_URL = os.getenv("BOOK_QUERY_URL")      # For read operations

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

@app.middleware("http")
async def check_jwt(request: Request, call_next):
    if request.url.path == "/status":
        return await call_next(request)

    token = request.headers.get("Authorization")
    if not token or not validate_jwt(token.replace("Bearer ", "", 1)):
        return JSONResponse(status_code=401, content={"message": "Invalid or missing token"})
    return await call_next(request)

# Write operations - route to Book Command service
@app.post("/books", response_model=BookResponse, status_code=201)
async def add_book(book: BookCreate):
    async with httpx.AsyncClient() as client:
        # Notice the /cmd/ path added to the URL
        response = await client.post(f"{BOOK_COMMAND_URL}/cmd/books", json=dict(book))
        if response.status_code != 201:
            raise HTTPException(status_code=response.status_code, detail=response.json().get("message"))
        return response.json()

# Read operations - route to Book Query service
@app.get("/books/{ISBN}", response_model=BookResponse)
@app.get("/books/isbn/{ISBN}", response_model=BookResponse)
async def get_book(ISBN: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BOOK_QUERY_URL}/books/{ISBN}")
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json().get("message"))
        return response.json()


@app.put("/books/{ISBN}", response_model=BookResponse)
async def update_book(ISBN: str, book: BookCreate):
    async with httpx.AsyncClient() as client:
        # Notice the /cmd/ path added to the URL
        response = await client.put(f"{BOOK_COMMAND_URL}/cmd/books/{ISBN}", json=dict(book))
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json().get("message"))
        book_data = response.json()
        return book_data

# Add new search endpoint
@app.get("/books")
async def search_books(keyword: str = Query(...)):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BOOK_QUERY_URL}/books?keyword={keyword}")
        
        # Handle 204 No Content
        if response.status_code == 204:
            return Response(status_code=204)
            
        # Handle errors
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json().get("message"))
            
        return response.json()

@app.get("/books/{ISBN}/related-books")
async def get_related_books(ISBN: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BOOK_QUERY_URL}/books/{ISBN}/related-books")
        if response.status_code == 204:
            return Response(status_code=204)
        if response.status_code not in (200, 204):
            raise HTTPException(status_code=response.status_code, detail=response.json().get("message"))
        book_data = response.json()
        return JSONResponse(content=book_data, status_code=response.status_code)

@app.post("/customers", response_model=CustomerResponse, status_code=201)
async def add_customer(customer: CustomerCreate):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{CUSTOMER_URL}/customers", json=dict(customer))
        if response.status_code != 201:
            raise HTTPException(status_code=response.status_code, detail=response.json().get("message"))
        return response.json()

@app.get("/customers/{id}", response_model=CustomerResponse)
async def get_customer(id: int):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{CUSTOMER_URL}/customers/{id}")
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json().get("message"))
        return response.json()

@app.get("/customers", response_model=CustomerResponse)
async def get_customer_by_userid(userId: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{CUSTOMER_URL}/customers", params={"userId": userId})
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json().get("message"))
        return response.json()

@app.get("/status", response_class=PlainTextResponse)
async def get_status():
    return "OK"