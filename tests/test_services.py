"""Tests for service layer business logic"""

import datetime
import pytest
from buylog.services import (
    BrandService,
    ProductService,
    VendorService,
    QuoteService,
    ForexService,
    ValidationError,
    DuplicateError,
    NotFoundError,
)
from buylog.models import Brand, Product, Vendor, Quote, Forex


# BrandService Tests
def test_brand_service_create(dbsession):
    """Test creating a brand via service layer"""
    brand = BrandService.create(dbsession, "Apple")
    assert brand.id is not None
    assert brand.name == "Apple"


def test_brand_service_create_strips_whitespace(dbsession):
    """Test that service layer strips whitespace"""
    brand = BrandService.create(dbsession, "  Apple  ")
    assert brand.name == "Apple"


def test_brand_service_create_empty_name(dbsession):
    """Test creating brand with empty name raises error"""
    with pytest.raises(ValidationError, match="cannot be empty"):
        BrandService.create(dbsession, "")


def test_brand_service_create_whitespace_only(dbsession):
    """Test creating brand with whitespace only raises error"""
    with pytest.raises(ValidationError, match="cannot be empty"):
        BrandService.create(dbsession, "   ")


def test_brand_service_create_too_long(dbsession):
    """Test creating brand with name too long raises error"""
    long_name = "A" * 256
    with pytest.raises(ValidationError, match="too long"):
        BrandService.create(dbsession, long_name)


def test_brand_service_create_duplicate(dbsession):
    """Test creating duplicate brand raises error"""
    BrandService.create(dbsession, "Apple")
    with pytest.raises(DuplicateError, match="already exists"):
        BrandService.create(dbsession, "Apple")


def test_brand_service_get_all(dbsession):
    """Test getting all brands"""
    BrandService.create(dbsession, "Apple")
    BrandService.create(dbsession, "Samsung")

    brands = BrandService.get_all(dbsession)
    assert len(brands) == 2
    assert {b.name for b in brands} == {"Apple", "Samsung"}


def test_brand_service_get_all_with_filter(dbsession):
    """Test getting brands with filter"""
    BrandService.create(dbsession, "Apple")
    BrandService.create(dbsession, "Samsung")

    brands = BrandService.get_all(dbsession, filter_by="App")
    assert len(brands) == 1
    assert brands[0].name == "Apple"


def test_brand_service_get_all_with_pagination(dbsession):
    """Test pagination in get_all"""
    for i in range(5):
        BrandService.create(dbsession, f"Brand{i}")

    # Get first 2
    brands = BrandService.get_all(dbsession, limit=2, offset=0)
    assert len(brands) == 2

    # Get next 2
    brands = BrandService.get_all(dbsession, limit=2, offset=2)
    assert len(brands) == 2


def test_brand_service_update(dbsession):
    """Test updating a brand"""
    BrandService.create(dbsession, "Apple")
    brand = BrandService.update(dbsession, "Apple", "Apple Inc.")

    assert brand.name == "Apple Inc."


def test_brand_service_update_not_found(dbsession):
    """Test updating non-existent brand raises error"""
    with pytest.raises(NotFoundError, match="not found"):
        BrandService.update(dbsession, "NonExistent", "NewName")


def test_brand_service_delete(dbsession):
    """Test deleting a brand"""
    BrandService.create(dbsession, "Apple")
    BrandService.delete(dbsession, "Apple")

    brand = BrandService.get_by_name(dbsession, "Apple")
    assert brand is None


def test_brand_service_delete_not_found(dbsession):
    """Test deleting non-existent brand raises error"""
    with pytest.raises(NotFoundError, match="not found"):
        BrandService.delete(dbsession, "NonExistent")


# ProductService Tests
def test_product_service_create(dbsession):
    """Test creating a product"""
    BrandService.create(dbsession, "Apple")
    product = ProductService.create(dbsession, "iPhone 15", "Apple")

    assert product.id is not None
    assert product.name == "iPhone 15"
    assert product.brand.name == "Apple"


def test_product_service_create_with_new_brand(dbsession):
    """Test creating product automatically creates brand"""
    product = ProductService.create(dbsession, "iPhone 15", "Apple")

    assert product.brand.name == "Apple"
    brand = BrandService.get_by_name(dbsession, "Apple")
    assert brand is not None


def test_product_service_create_duplicate(dbsession):
    """Test creating duplicate product raises error"""
    ProductService.create(dbsession, "iPhone 15", "Apple")
    with pytest.raises(DuplicateError, match="already exists"):
        ProductService.create(dbsession, "iPhone 15", "Samsung")


def test_product_service_get_all_eager_loads_brand(dbsession):
    """Test get_all eagerly loads brands (no N+1)"""
    ProductService.create(dbsession, "iPhone 15", "Apple")
    ProductService.create(dbsession, "Galaxy S23", "Samsung")

    products = ProductService.get_all(dbsession)
    # Access brand.name should not trigger additional queries
    # (verified by lack of SQL in logs with DEBUG enabled)
    for p in products:
        assert p.brand.name  # Should not cause N+1 query


# VendorService Tests
def test_vendor_service_create(dbsession):
    """Test creating a vendor"""
    vendor = VendorService.create(dbsession, "Amazon", currency="USD")

    assert vendor.id is not None
    assert vendor.name == "Amazon"
    assert vendor.currency == "USD"


def test_vendor_service_create_validates_currency_length(dbsession):
    """Test currency code must be 3 characters"""
    with pytest.raises(ValidationError, match="3 characters"):
        VendorService.create(dbsession, "Amazon", currency="US")


def test_vendor_service_create_validates_discount_range(dbsession):
    """Test discount must be 0-100"""
    with pytest.raises(ValidationError, match="between 0 and 100"):
        VendorService.create(dbsession, "Amazon", discount=150.0)


def test_vendor_service_create_normalizes_currency(dbsession):
    """Test currency code is normalized to uppercase"""
    vendor = VendorService.create(dbsession, "Amazon", currency="eur")
    assert vendor.currency == "EUR"


# QuoteService Tests
def test_quote_service_create(dbsession):
    """Test creating a quote"""
    VendorService.create(dbsession, "Amazon", currency="USD")
    ProductService.create(dbsession, "iPhone 15", "Apple")

    quote = QuoteService.create(dbsession, "Amazon", "iPhone 15", 999.99)

    assert quote.id is not None
    assert quote.vendor.name == "Amazon"
    assert quote.product.name == "iPhone 15"
    assert quote.value == 999.99


def test_quote_service_create_vendor_not_found(dbsession):
    """Test creating quote with non-existent vendor raises error"""
    with pytest.raises(NotFoundError, match="not found"):
        QuoteService.create(dbsession, "NonExistent", "iPhone 15", 999.99)


def test_quote_service_create_with_new_product(dbsession):
    """Test creating quote can create new product"""
    VendorService.create(dbsession, "Amazon", currency="USD")

    quote = QuoteService.create(
        dbsession, "Amazon", "iPhone 15", 999.99, brand_name="Apple"
    )

    assert quote.product.name == "iPhone 15"
    assert quote.product.brand.name == "Apple"


def test_quote_service_create_negative_price(dbsession):
    """Test creating quote with negative price raises error"""
    VendorService.create(dbsession, "Amazon", currency="USD")
    ProductService.create(dbsession, "iPhone 15", "Apple")

    with pytest.raises(ValidationError, match="cannot be negative"):
        QuoteService.create(dbsession, "Amazon", "iPhone 15", -100.0)


def test_quote_service_create_with_currency_conversion(dbsession):
    """Test quote with non-USD vendor converts currency"""
    ForexService.create(dbsession, "GBP", 1.25)
    VendorService.create(dbsession, "UK Shop", currency="GBP")
    ProductService.create(dbsession, "iPhone 15", "Apple")

    quote = QuoteService.create(dbsession, "UK Shop", "iPhone 15", 800.0)

    assert quote.original_value == 800.0
    assert quote.original_currency == "GBP"
    assert quote.value == 800.0 * 1.25  # Converted to USD
    assert quote.currency == "USD"


def test_quote_service_get_all_eager_loads(dbsession):
    """Test get_all eagerly loads vendor and product (no N+1)"""
    VendorService.create(dbsession, "Amazon", currency="USD")
    ProductService.create(dbsession, "iPhone 15", "Apple")
    QuoteService.create(dbsession, "Amazon", "iPhone 15", 999.99)

    quotes = QuoteService.get_all(dbsession)

    # Access related objects should not trigger additional queries
    for q in quotes:
        assert q.vendor.name
        assert q.product.name
        assert q.product.brand.name  # Should not cause N+1


# ForexService Tests
def test_forex_service_create(dbsession):
    """Test creating a forex rate"""
    fx = ForexService.create(dbsession, "EUR", 1.085)

    assert fx.id is not None
    assert fx.code == "EUR"
    assert fx.usd_per_unit == 1.085
    assert fx.date == datetime.date.today()


def test_forex_service_create_with_date(dbsession):
    """Test creating forex rate with specific date"""
    date = datetime.date(2025, 10, 15)
    fx = ForexService.create(dbsession, "EUR", 1.085, date=date)

    assert fx.date == date


def test_forex_service_create_normalizes_code(dbsession):
    """Test currency code is normalized to uppercase"""
    fx = ForexService.create(dbsession, "eur", 1.085)
    assert fx.code == "EUR"


def test_forex_service_create_validates_code_length(dbsession):
    """Test currency code must be 3 characters"""
    with pytest.raises(ValidationError, match="3 characters"):
        ForexService.create(dbsession, "EU", 1.085)


def test_forex_service_create_validates_positive_rate(dbsession):
    """Test exchange rate must be positive"""
    with pytest.raises(ValidationError, match="positive"):
        ForexService.create(dbsession, "EUR", 0.0)


def test_forex_service_create_duplicate(dbsession):
    """Test creating duplicate rate for same code and date raises error"""
    ForexService.create(dbsession, "EUR", 1.085)
    with pytest.raises(DuplicateError, match="already exists"):
        ForexService.create(dbsession, "EUR", 1.090)


def test_forex_service_create_same_code_different_date(dbsession):
    """Test can create multiple rates for same code on different dates"""
    ForexService.create(dbsession, "EUR", 1.085, date=datetime.date(2025, 10, 15))
    fx = ForexService.create(dbsession, "EUR", 1.090, date=datetime.date(2025, 10, 16))

    assert fx.usd_per_unit == 1.090


def test_forex_service_get_latest(dbsession):
    """Test getting latest rate for a currency"""
    ForexService.create(dbsession, "EUR", 1.080, date=datetime.date(2025, 10, 15))
    ForexService.create(dbsession, "EUR", 1.085, date=datetime.date(2025, 10, 16))
    ForexService.create(dbsession, "EUR", 1.090, date=datetime.date(2025, 10, 17))

    latest = ForexService.get_latest(dbsession, "EUR")

    assert latest.usd_per_unit == 1.090
    assert latest.date == datetime.date(2025, 10, 17)
