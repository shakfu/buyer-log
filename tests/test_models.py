import pytest
from sqlalchemy.exc import IntegrityError

from buylog.models import Base, Brand, Product, Vendor, Quote, Forex


# Brand Tests
def test_brand_creation(dbsession):
    """Test brand can be created with valid name"""
    brand = Brand(name="Apple")
    dbsession.add(brand)
    dbsession.flush()

    assert brand.id is not None
    assert brand.name == "Apple"
    assert repr(brand) == "<Brand(name='Apple')>"


def test_brand_by_name_exists(dbsession):
    """Test Brand.by_name() returns existing brand"""
    brand = Brand(name="Apple")
    dbsession.add(brand)
    dbsession.commit()

    result = Brand.by_name(dbsession, "Apple")
    assert result is not None
    assert result.name == "Apple"
    assert result.id == brand.id


def test_brand_by_name_not_exists(dbsession):
    """Test Brand.by_name() returns None for non-existent brand"""
    result = Brand.by_name(dbsession, "NonExistent")
    assert result is None


def test_brand_unique_constraint(dbsession):
    """Test duplicate brand names are rejected"""
    brand1 = Brand(name="Apple")
    brand2 = Brand(name="Apple")
    dbsession.add(brand1)
    dbsession.add(brand2)

    with pytest.raises(IntegrityError):
        dbsession.commit()


def test_brand_products_relationship(dbsession):
    """Test brand can have multiple products"""
    brand = Brand(name="Apple")
    product1 = Product(name="iPhone 15", brand=brand)
    product2 = Product(name="iPhone 14", brand=brand)
    dbsession.add_all([brand, product1, product2])
    dbsession.commit()

    assert len(brand.products) == 2
    assert product1 in brand.products
    assert product2 in brand.products


# Product Tests
def test_product_creation(dbsession):
    """Test product can be created with brand"""
    brand = Brand(name="Apple")
    product = Product(name="iPhone 15", brand=brand)
    dbsession.add_all([brand, product])
    dbsession.flush()

    assert product.id is not None
    assert product.name == "iPhone 15"
    assert product.brand == brand
    assert product.brand_id == brand.id


def test_product_by_name_exists(dbsession):
    """Test Product.by_name() returns existing product"""
    brand = Brand(name="Apple")
    product = Product(name="iPhone 15", brand=brand)
    dbsession.add_all([brand, product])
    dbsession.commit()

    result = Product.by_name(dbsession, "iPhone 15")
    assert result is not None
    assert result.name == "iPhone 15"
    assert result.brand.name == "Apple"


def test_product_unique_constraint(dbsession):
    """Test duplicate product names are rejected"""
    brand = Brand(name="Apple")
    product1 = Product(name="iPhone 15", brand=brand)
    product2 = Product(name="iPhone 15", brand=brand)
    dbsession.add_all([brand, product1, product2])

    with pytest.raises(IntegrityError):
        dbsession.commit()


# Vendor Tests
def test_vendor_creation(dbsession):
    """Test vendor can be created with currency"""
    vendor = Vendor(name="Amazon", currency="USD", discount_code="SAVE10", discount=10.0)
    dbsession.add(vendor)
    dbsession.flush()

    assert vendor.id is not None
    assert vendor.name == "Amazon"
    assert vendor.currency == "USD"
    assert vendor.discount_code == "SAVE10"
    assert vendor.discount == 10.0


def test_vendor_by_name_exists(dbsession):
    """Test Vendor.by_name() returns existing vendor"""
    vendor = Vendor(name="Amazon", currency="USD")
    dbsession.add(vendor)
    dbsession.commit()

    result = Vendor.by_name(dbsession, "Amazon")
    assert result is not None
    assert result.name == "Amazon"


def test_vendor_unique_constraint(dbsession):
    """Test duplicate vendor names are rejected"""
    vendor1 = Vendor(name="Amazon", currency="USD")
    vendor2 = Vendor(name="Amazon", currency="GBP")
    dbsession.add_all([vendor1, vendor2])

    with pytest.raises(IntegrityError):
        dbsession.commit()


def test_vendor_brand_relationship(dbsession):
    """Test many-to-many relationship between vendors and brands"""
    vendor = Vendor(name="Amazon", currency="USD")
    brand1 = Brand(name="Apple")
    brand2 = Brand(name="Samsung")
    vendor.brands = [brand1, brand2]
    dbsession.add_all([vendor, brand1, brand2])
    dbsession.commit()

    assert len(vendor.brands) == 2
    assert brand1 in vendor.brands
    assert brand2 in vendor.brands
    assert vendor in brand1.vendors
    assert vendor in brand2.vendors


def test_vendor_add_product_creates_new_brand(dbsession):
    """Test Vendor.add_product() creates brand if not exists"""
    vendor = Vendor(name="Amazon", currency="USD")
    dbsession.add(vendor)
    dbsession.flush()

    vendor.add_product(dbsession, "NewBrand", "NewProduct", 99.99)
    dbsession.commit()

    brand = Brand.by_name(dbsession, "NewBrand")
    assert brand is not None
    product = Product.by_name(dbsession, "NewProduct")
    assert product is not None
    assert product.brand == brand


def test_vendor_add_product_creates_quote(dbsession):
    """Test Vendor.add_product() creates a quote"""
    vendor = Vendor(name="Amazon", currency="USD")
    dbsession.add(vendor)
    dbsession.flush()

    vendor.add_product(dbsession, "Apple", "iPhone 15", 999.99, discount=5.0)
    dbsession.commit()

    product = Product.by_name(dbsession, "iPhone 15")
    assert len(product.quotes) == 1
    quote = product.quotes[0]
    assert quote.vendor == vendor
    assert quote.value == 999.99
    assert quote.discount == 5.0


# Quote Tests
def test_quote_creation(dbsession):
    """Test quote can be created with vendor and product"""
    brand = Brand(name="Apple")
    product = Product(name="iPhone 15", brand=brand)
    vendor = Vendor(name="Amazon", currency="USD")
    quote = Quote(product=product, vendor=vendor, currency="USD", value=999.99)
    dbsession.add_all([brand, product, vendor, quote])
    dbsession.flush()

    assert quote.id is not None
    assert quote.product == product
    assert quote.vendor == vendor
    assert quote.value == 999.99
    assert quote.currency == "USD"


def test_quote_repr(dbsession):
    """Test quote string representation"""
    brand = Brand(name="Apple")
    product = Product(name="iPhone 15", brand=brand)
    vendor = Vendor(name="Amazon", currency="USD")
    quote = Quote(product=product, vendor=vendor, currency="USD", value=999.99)
    dbsession.add_all([brand, product, vendor, quote])
    dbsession.commit()

    assert repr(quote) == "<Quote(Amazon / Apple iPhone 15 / 999.99 USD)>"


def test_quote_with_original_currency(dbsession):
    """Test quote stores original currency and value"""
    brand = Brand(name="Apple")
    product = Product(name="iPhone 15", brand=brand)
    vendor = Vendor(name="UK Shop", currency="GBP")
    quote = Quote(
        product=product,
        vendor=vendor,
        currency="USD",
        value=1250.0,
        original_value=1000.0,
        original_currency="GBP",
    )
    dbsession.add_all([brand, product, vendor, quote])
    dbsession.commit()

    assert quote.original_value == 1000.0
    assert quote.original_currency == "GBP"
    assert quote.value == 1250.0
    assert quote.currency == "USD"


# Forex Tests
def test_forex_creation(dbsession):
    """Test forex rate can be created"""
    import datetime

    fx = Forex(code="EUR", usd_per_unit=1.085)
    dbsession.add(fx)
    dbsession.flush()

    assert fx.id is not None
    assert fx.code == "EUR"
    assert fx.usd_per_unit == 1.085
    assert fx.date is not None
    # Test backward compatibility property
    assert abs(fx.units_per_usd - (1.0 / 1.085)) < 0.001


def test_forex_repr(dbsession):
    """Test forex string representation"""
    import datetime

    fx = Forex(code="EUR", usd_per_unit=1.085, date=datetime.date(2025, 10, 17))
    dbsession.add(fx)
    dbsession.commit()

    assert "EUR" in repr(fx)
    assert "USD" in repr(fx)
    assert "1.085" in repr(fx)


def test_forex_multiple_currencies(dbsession):
    """Test multiple forex rates can be stored"""
    eur = Forex(code="EUR", usd_per_unit=1.085)
    gbp = Forex(code="GBP", usd_per_unit=1.292)
    jpy = Forex(code="JPY", usd_per_unit=0.0067)
    dbsession.add_all([eur, gbp, jpy])
    dbsession.commit()

    assert dbsession.query(Forex).count() == 3


def test_forex_historical_rates(dbsession):
    """Test forex rates can be stored with different dates"""
    import datetime

    # Same currency, different dates
    eur_today = Forex(code="EUR", usd_per_unit=1.085, date=datetime.date(2025, 10, 17))
    eur_yesterday = Forex(code="EUR", usd_per_unit=1.080, date=datetime.date(2025, 10, 16))
    dbsession.add_all([eur_today, eur_yesterday])
    dbsession.commit()

    # Query rates for specific date
    rates = dbsession.query(Forex).filter(Forex.code == "EUR").all()
    assert len(rates) == 2


def test_forex_units_per_usd_property(dbsession):
    """Test backward compatibility property calculation"""
    fx = Forex(code="EUR", usd_per_unit=1.085)
    dbsession.add(fx)
    dbsession.commit()

    # units_per_usd should be 1/usd_per_unit
    expected = 1.0 / 1.085
    assert abs(fx.units_per_usd - expected) < 0.001


# Integration Tests
def test_full_workflow(dbsession):
    """Test complete workflow: brand -> product -> vendor -> quote"""
    # Create forex rates
    eur = Forex(code="EUR", usd_per_unit=1.085)
    gbp = Forex(code="GBP", usd_per_unit=1.292)

    # Create vendors
    acme_corp = Vendor(name="acme-corp", currency="USD", discount_code="abc123", discount=0.1)
    amazon = Vendor(name="amazon", currency="GBP")

    # Create brands
    yamaha = Brand(name="yamaha")
    samsung = Brand(name="samsung")
    microsoft = Brand(name="microsoft")

    # Create products
    product_a = Product(name="productA", brand=yamaha)
    product_b = Product(name="productB", brand=samsung)
    product_c = Product(name="productC", brand=microsoft)

    # Create price quotes
    quote1 = Quote(product=product_a, vendor=acme_corp, currency="USD", value=280)
    quote2 = Quote(product=product_a, vendor=amazon, currency="GBP", value=210)

    # Set up relationships
    acme_corp.brands = [yamaha, samsung]
    amazon.brands = [yamaha, samsung, microsoft]

    # Test vendor.add_product
    acme_corp.add_product(dbsession, "sony", "walkman", 99.99)

    dbsession.add_all(
        [
            eur,
            gbp,
            acme_corp,
            amazon,
            yamaha,
            samsung,
            microsoft,
            product_a,
            product_b,
            product_c,
            quote1,
            quote2,
        ]
    )
    dbsession.flush()

    # Assertions
    assert product_a.name == "productA"
    assert Product.by_name(dbsession, "productB").brand.name == "samsung"
    assert repr(product_a) == "<Product(name='productA')>"
    assert "EUR" in repr(eur)
    assert "USD" in repr(eur)
    assert repr(quote1) == "<Quote(acme-corp / yamaha productA / 280 USD)>"
    assert "walkman" in [p.name for p in dbsession.query(Product).all()]

    # Additional assertions
    # Note: add_product creates "sony" brand and adds it to acme_corp.brands
    assert len(acme_corp.brands) == 3  # yamaha, samsung, sony
    assert len(amazon.brands) == 3
    assert product_a.quotes[0].vendor == acme_corp
    sony_brand = Brand.by_name(dbsession, "sony")
    assert sony_brand is not None
    assert sony_brand in acme_corp.brands
    walkman = Product.by_name(dbsession, "walkman")
    assert walkman.brand == sony_brand
