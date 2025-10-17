#!/usr/bin/env python3
"""
Pydantic schemas for input validation and API documentation.

These schemas provide:
- Input validation with clear error messages
- Type safety
- Automatic API documentation generation
- Serialization/deserialization
"""

import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict


class BrandCreate(BaseModel):
    """Schema for creating a new brand"""

    name: str = Field(..., min_length=1, max_length=255, description="Brand name")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and normalize brand name"""
        v = v.strip()
        if not v:
            raise ValueError("Brand name cannot be empty or whitespace")
        return v


class BrandUpdate(BaseModel):
    """Schema for updating a brand"""

    new_name: str = Field(..., min_length=1, max_length=255, description="New brand name")

    @field_validator("new_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and normalize brand name"""
        v = v.strip()
        if not v:
            raise ValueError("Brand name cannot be empty or whitespace")
        return v


class BrandResponse(BaseModel):
    """Schema for brand responses"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    product_count: Optional[int] = Field(default=0, description="Number of products")


class ProductCreate(BaseModel):
    """Schema for creating a new product"""

    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    brand_name: str = Field(..., min_length=1, max_length=255, description="Brand name")

    @field_validator("name", "brand_name")
    @classmethod
    def validate_names(cls, v: str) -> str:
        """Validate and normalize names"""
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty or whitespace")
        return v


class ProductResponse(BaseModel):
    """Schema for product responses"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    brand_name: Optional[str] = Field(default=None, description="Brand name")


class VendorCreate(BaseModel):
    """Schema for creating a new vendor"""

    name: str = Field(..., min_length=1, max_length=255, description="Vendor name")
    currency: str = Field(
        default="USD",
        min_length=3,
        max_length=3,
        description="Currency code (ISO 4217)",
    )
    discount_code: Optional[str] = Field(
        default=None, max_length=50, description="Optional discount code"
    )
    discount: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Discount percentage (0-100)"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and normalize vendor name"""
        v = v.strip()
        if not v:
            raise ValueError("Vendor name cannot be empty or whitespace")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate and normalize currency code"""
        v = v.strip().upper()
        if len(v) != 3:
            raise ValueError("Currency code must be exactly 3 characters (ISO 4217)")
        if not v.isalpha():
            raise ValueError("Currency code must contain only letters")
        return v


class VendorResponse(BaseModel):
    """Schema for vendor responses"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    currency: str
    discount_code: Optional[str] = None
    discount: float
    quote_count: Optional[int] = Field(default=0, description="Number of quotes")


class QuoteCreate(BaseModel):
    """Schema for creating a new quote"""

    vendor_name: str = Field(..., min_length=1, max_length=255, description="Vendor name")
    product_name: str = Field(..., min_length=1, max_length=255, description="Product name")
    price: float = Field(..., gt=0, description="Price (must be positive)")
    brand_name: Optional[str] = Field(
        default=None, max_length=255, description="Brand name (for new products)"
    )

    @field_validator("vendor_name", "product_name", "brand_name")
    @classmethod
    def validate_names(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize names"""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Name cannot be empty or whitespace")
        return v


class QuoteResponse(BaseModel):
    """Schema for quote responses"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor_name: Optional[str] = None
    product_name: Optional[str] = None
    brand_name: Optional[str] = None
    value: float
    currency: str
    original_value: Optional[float] = None
    original_currency: Optional[str] = None


class ForexCreate(BaseModel):
    """Schema for creating a forex rate"""

    code: str = Field(
        ..., min_length=3, max_length=3, description="Currency code (ISO 4217)"
    )
    usd_per_unit: float = Field(..., gt=0, description="USD value per unit of currency")
    date: Optional[datetime.date] = Field(
        default=None, description="Date for rate (defaults to today)"
    )

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Validate and normalize currency code"""
        v = v.strip().upper()
        if len(v) != 3:
            raise ValueError("Currency code must be exactly 3 characters (ISO 4217)")
        if not v.isalpha():
            raise ValueError("Currency code must contain only letters")
        return v


class ForexResponse(BaseModel):
    """Schema for forex rate responses"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    usd_per_unit: float
    date: datetime.date


class PaginationParams(BaseModel):
    """Schema for pagination parameters"""

    limit: int = Field(default=100, ge=1, le=1000, description="Maximum number of results")
    offset: int = Field(default=0, ge=0, description="Number of results to skip")
    filter_by: Optional[str] = Field(
        default=None, max_length=255, description="Optional filter string"
    )


class PaginatedResponse(BaseModel):
    """Generic schema for paginated responses"""

    items: List[BaseModel]
    total: int
    limit: int
    offset: int
    has_more: bool

    model_config = ConfigDict(from_attributes=True)
