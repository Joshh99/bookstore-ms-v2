from pydantic import BaseModel, EmailStr, constr, field_validator, Field, StrictInt, StrictFloat
from fastapi import HTTPException
from typing import Optional, Union

# Request model for Customer validation
class CustomerBase(BaseModel):
    userId: EmailStr  # Required, must be a valid email
    name: constr(min_length=1)  # Required
    phone: constr(min_length=1)  # Required
    address: constr(min_length=1)  # Required
    address2: Optional[str] = None  # Optional
    city: constr(min_length=1)  # Required
    state: constr(max_length=2, min_length=2)  # Required, exactly 2 characters
    zipcode: str  # Required

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        us_states = {
            "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN",
            "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV",
            "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN",
            "TX", "UT", "VT", "VA", "WA", "WI", "WY"
        }
        if v.upper() not in us_states:
            raise HTTPException(status_code=400, detail="State must be a valid 2-letter US state abbreviation")
        return v.upper()

# Request model for Book validation
class BookBase(BaseModel):
    ISBN: constr(min_length=1)  # Required
    title: constr(min_length=1)  # Required
    Author: constr(min_length=1)  # Required
    description: constr(min_length=1)  # Required
    genre: constr(min_length=1)  # Required
    price: StrictFloat = Field(..., gt=0)  # Required, must be > 0
    quantity: StrictInt = Field(..., gt=0)  # Required, must be > 0

    @field_validator("price")
    def validate_price(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Price must be greater than 0")
        # Convert to string to check decimal places
        price_str = str(v)
        if '.' not in price_str:
            raise ValueError("Price must have exactly 2 decimal places")
        decimal_part = price_str.split('.')[1]
        if len(decimal_part) > 2:
            raise HTTPException(status_code=400, detail="Must have at most 2 decimal places.")
        return v

    @field_validator("quantity")
    def validate_quantity(cls, v: int) -> int:
        if v <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be greater than 0")
        return v

class BookCreate(BookBase):
    pass

class BookResponse(BookBase):
    genre: Union[str, int]

class CustomerCreate(CustomerBase):
    pass

class CustomerResponse(CustomerBase):
    id: int
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zipcode: Optional[str]