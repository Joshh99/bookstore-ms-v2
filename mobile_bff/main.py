from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse, JSONResponse, Response
from dotenv import load_dotenv
import httpx
import os

from pydantic import EmailStr

from utils import validate_jwt
from schemas import BookCreate, BookResponse, CustomerCreate, CustomerResponse

app = FastAPI()
# Load environment variables from file
load_dotenv()


CUSTOMER_URL = os.getenv("CUSTOMER_URL")
BOOK_URL = os.getenv("BOOK_URL")

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

# middleware to screen jwt
@app.middleware("http")
async def check_jwt(request: Request, call_next):
    if request.url.path == "/status":
        return await call_next(request)

    token = request.headers.get("Authorization")
    if not token or not validate_jwt(token.replace("Bearer ", "", 1)):
        return JSONResponse(status_code=401, content={"message": "Invalid or missing token"})
    return await call_next(request)

# endpoint to add a book
@app.post("/books", response_model=BookResponse, status_code=201)
async def add_book(book: BookCreate):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BOOK_URL}/books", json=dict(book))
        if response.status_code != 201:
            raise HTTPException(status_code=response.status_code, detail=response.json().get("message"))
        return response.json()

# Endpoint to update a book
@app.put("/books/{ISBN}" , response_model=BookResponse)
async def update_book(ISBN: str, book: BookCreate):
    async with httpx.AsyncClient() as client:
        response = await client.put(f"{BOOK_URL}/books/{ISBN}", json=dict(book))
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json().get("message"))
        book_data = response.json()
        return book_data

# Endpoint to get books
@app.get("/books/{ISBN}", response_model=BookResponse)
@app.get("/books/isbn/{ISBN}", response_model=BookResponse)
async def get_book(ISBN: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BOOK_URL}/books/{ISBN}")
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json().get("message"))
        book_data = response.json()
        if book_data.get("genre") == "non-fiction":
            book_data["genre"] = 3
        return book_data


@app.get("/books/{ISBN}/related-books")
async def get_recommend_book(ISBN: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BOOK_URL}/books/{ISBN}/related-books")
        if response.status_code == 204:
            return Response(status_code=204)
        book_data = response.json()
        return JSONResponse(content=book_data, status_code=response.status_code)



#add a new customer
@app.post("/customers", response_model=CustomerResponse, status_code=201)
async def add_customer(customer: CustomerCreate):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{CUSTOMER_URL}/customers", json=dict(customer))
        if response.status_code != 201:
            raise HTTPException(status_code=response.status_code, detail=response.json().get("message"))
        return response.json()

#Get customer by id
@app.get("/customers/{id}", response_model=CustomerResponse, response_model_exclude_unset=True)
async def get_customer(id: int):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{CUSTOMER_URL}/customers/{id}")
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json().get("message"))
        customer_data = response.json()
        for field in ["address", "address2", "city", "state", "zipcode"]:
            customer_data.pop(field, None)

        jsonResponse = JSONResponse(content=customer_data)
        return jsonResponse


# get endpoint for customers with query
@app.get("/customers", response_model=CustomerResponse, response_model_exclude_unset=True)
async def get_customer_by_userid(userId: EmailStr = Query(...)):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{CUSTOMER_URL}/customers?userId={userId}")
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json().get("message"))
        customer_data = response.json()
        for field in ["address", "address2", "city", "state", "zipcode"]:
            customer_data.pop(field, None)
        jsonResponse = JSONResponse(content=customer_data)
        return jsonResponse


#status check
@app.get("/status", response_class=PlainTextResponse)
async def get_status():
    return "OK"