from contextlib import asynccontextmanager  # Add for lifespan
from fastapi import FastAPI, HTTPException, status, Request, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, EmailStr, constr, field_validator, Field, StrictInt, StrictFloat
from sqlalchemy.exc import IntegrityError
from database import Customer, create_db_and_tables, engine, Session, select,APP_URL  # Import from database.py
from schemas import CustomerCreate
from kafka import KafkaProducer
import json
import os
from dotenv import load_dotenv


KAFKA_BROKER = os.getenv("KAFKA_BROKER").split(",")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC")
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

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

@app.get("/customers/status", status_code=status.HTTP_200_OK, response_class=PlainTextResponse)
async def get_status():
    return "OK"

# POST /customers - Add a customer
@app.post("/customers", status_code=status.HTTP_201_CREATED)
async def add_customer(customer_data: CustomerCreate):
    with Session(engine) as session:
        customer = Customer(**dict(customer_data))
        existing_customer = session.exec(select(Customer).where(Customer.userId == customer.userId)).first()
        if existing_customer:
            raise HTTPException(status_code=422, detail="This user ID already exists in the system.")
        session.add(customer)
        session.commit()
        session.refresh(customer)
        response = JSONResponse(content=dict(customer))

        # Publish to Kafka
        producer.send(KAFKA_TOPIC, dict(customer))
        producer.flush()

        response.headers["Location"] = f"{APP_URL}/customers/{customer.id}"
        response.status_code = status.HTTP_201_CREATED
        return response



# GET /customers/{id} - Retrieve customer by numeric ID
@app.get("/customers/{id}", status_code=status.HTTP_200_OK)
async def get_customer_by_id(id: int):
    with Session(engine) as session:
        customer = session.exec(select(Customer).where(Customer.id == id)).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer ID not found")
        return customer


# GET /customers?userId={userId} - Retrieve customer by user ID
@app.get("/customers", status_code=status.HTTP_200_OK)
async def get_customer_by_user_id(userId: EmailStr = Query(...)):
    with Session(engine) as session:
        customer = session.exec(select(Customer).where(Customer.userId == userId)).first()
        if not customer:
            raise HTTPException(status_code=404, detail="User ID not found")
        return customer


# Status endpoint
