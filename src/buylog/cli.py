#!/usr/bin/env python3
"""CLI interface for buylog tool with CRUD operations"""

import argparse
from pathlib import Path
from typing import Optional
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session as SessionType
from tabulate import tabulate
from .models import Base, Brand, Product, Vendor, Quote, Forex
from .config import Config

# Setup logging
logger = Config.setup_logging()

# Database setup
engine = Config.get_engine()
Base.metadata.create_all(engine)
Session = Config.get_session_maker()


def add_brand(session: SessionType, name: str) -> Optional[Brand]:
    """
    Add a new brand to the database.

    Args:
        session: Active database session
        name: Brand name to add

    Returns:
        Created or existing Brand instance, or None on error

    Example:
        >>> brand = add_brand(session, "Apple")
        Added brand: Apple
    """
    from .services import BrandService, DuplicateError, ValidationError

    try:
        brand = BrandService.create(session, name)
        print(f"Added brand: {name}")
        return brand
    except DuplicateError:
        print(f"Brand '{name}' already exists")
        return BrandService.get_by_name(session, name)
    except ValidationError as e:
        print(f"Error: {e}")
        return None


def add_product(session, brand_name, product_name):
    """Add a new product under a brand"""
    brand = Brand.by_name(session, brand_name)
    if not brand:
        print(f"Brand '{brand_name}' not found. Adding it first.")
        brand = add_brand(session, brand_name)

    existing = Product.by_name(session, product_name)
    if existing:
        print(f"Product '{product_name}' already exists")
        return existing

    product = Product(name=product_name, brand=brand)
    session.add(product)
    session.commit()
    print(f"Added product: {product_name} under brand: {brand_name}")
    return product


def add_vendor(session, name, currency="USD", discount_code=None, discount=0.0):
    """Add a new vendor"""
    existing = Vendor.by_name(session, name)
    if existing:
        print(f"Vendor '{name}' already exists")
        return existing

    vendor = Vendor(
        name=name, currency=currency, discount_code=discount_code, discount=discount
    )
    session.add(vendor)
    session.commit()
    print(f"Added vendor: {name} (currency: {currency})")
    return vendor


def add_quote(
    session,
    vendor_name,
    product_name,
    price,
    brand_name=None,
    shipping_cost=None,
    tax_rate=None,
):
    """Add a quote from a vendor for a product"""
    from .services import QuoteHistoryService

    vendor = Vendor.by_name(session, vendor_name)
    if not vendor:
        create_vendor = input(f"Vendor '{vendor_name}' not found. Create it? (y/n): ")
        if create_vendor.lower() == "y":
            vendor = add_vendor(session, vendor_name)
        else:
            return None

    product = Product.by_name(session, product_name)
    if not product:
        create_product = input(
            f"Product '{product_name}' not found. Create it? (y/n): "
        )
        if create_product.lower() == "y":
            if not brand_name:
                brand_name = input("Enter brand name for the new product: ")
            product = add_product(session, brand_name, product_name)
        else:
            return None

    value = float(price)
    original_value = None
    original_currency = None

    if vendor.currency != "USD":
        fx_rate = session.execute(
            select(Forex).where(Forex.code == vendor.currency)
        ).scalar_one_or_none()
        if not fx_rate:
            print(
                f"Forex rate for '{vendor.currency}' not found. Please add it using the add-fx command."
            )
            return None
        original_value = value
        original_currency = vendor.currency
        value = value * fx_rate.usd_per_unit

    quote = Quote(
        vendor=vendor,
        product=product,
        currency="USD",
        value=value,
        original_value=original_value,
        original_currency=original_currency,
        shipping_cost=shipping_cost,
        tax_rate=tax_rate,
    )
    session.add(quote)
    session.commit()

    # Record creation in history
    QuoteHistoryService.record_change(session, quote, None, value, "create")

    print(f"Added quote: {vendor_name} -> {product_name} = {price} {vendor.currency}")
    if shipping_cost:
        print(f"  Shipping: {shipping_cost}")
    if tax_rate:
        print(f"  Tax rate: {tax_rate}%")
    return quote


def add_fx(session, code, usd_per_unit, date=None):
    """Add a new forex rate for a specific date (defaults to today)"""
    import datetime

    # Use provided date or default to today
    if date is None:
        date = datetime.date.today()
    elif isinstance(date, str):
        # Parse date string if provided
        try:
            date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            print("Error: Invalid date format. Use YYYY-MM-DD")
            return None

    # Check if rate already exists for this code and date
    existing = session.execute(
        select(Forex).where(Forex.code == code, Forex.date == date)
    ).scalar_one_or_none()
    if existing:
        print(f"Forex rate for '{code}' on {date} already exists")
        return existing

    fx = Forex(code=code, usd_per_unit=usd_per_unit, date=date)
    session.add(fx)
    session.commit()
    print(f"Added forex rate: {code} = {usd_per_unit} USD per unit on {date}")
    return fx


def list_entities(
    session: SessionType,
    entity_type: str,
    filter_by: Optional[str] = None,
    sort_by: Optional[str] = None,
    limit: int = 100,
) -> None:
    """
    List all entities of a given type with pagination.

    Uses service layer with eager loading to avoid N+1 query problems.

    Args:
        session: Active database session
        entity_type: Type of entity to list ("brands", "products", "vendors", "quotes")
        filter_by: Optional name filter for case-insensitive partial match
        sort_by: Optional column to sort by (currently unused, reserved for future)
        limit: Maximum number of results to display (default: 100)

    Example:
        >>> list_entities(session, "brands", filter_by="Apple")
        ╒══════╤═══════╤═════════════════════╕
        │   ID │ Name  │ Products            │
        ╞══════╪═══════╪═════════════════════╡
        │    1 │ Apple │ iPhone 15, iPhone 14│
        ╘══════╧═══════╧═════════════════════╛
    """
    from .services import BrandService, ProductService, VendorService, QuoteService

    if entity_type == "brands":
        brands = BrandService.get_all(session, filter_by=filter_by, limit=limit)
        headers = ["ID", "Name", "Products"]
        data = [[b.id, b.name, ", ".join([p.name for p in b.products])] for b in brands]
        print(tabulate(data, headers=headers, tablefmt="grid"))

    elif entity_type == "products":
        products = ProductService.get_all(session, filter_by=filter_by, limit=limit)
        headers = ["ID", "Name", "Brand"]
        data = [[p.id, p.name, p.brand.name] for p in products]
        print(tabulate(data, headers=headers, tablefmt="grid"))

    elif entity_type == "vendors":
        vendors = VendorService.get_all(session, filter_by=filter_by, limit=limit)
        headers = ["ID", "Name", "Currency", "Quotes"]
        data = [[v.id, v.name, v.currency, len(v.quotes)] for v in vendors]
        print(tabulate(data, headers=headers, tablefmt="grid"))

    elif entity_type == "quotes":
        quotes = QuoteService.get_all(session, filter_by=filter_by, limit=limit)
        headers = ["ID", "Vendor", "Product", "Price", "Currency"]
        data = [
            [
                q.id,
                q.vendor.name,
                f"{q.product.brand.name} {q.product.name}",
                q.value,
                q.currency,
            ]
            for q in quotes
        ]
        print(tabulate(data, headers=headers, tablefmt="grid"))


def delete_entity(session, entity_type, name=None, id=None):
    """Delete an entity by name or ID"""

    if entity_type == "quote":
        if not id:
            print("Please provide the ID of the quote to delete using --id.")

            return

        entity = session.get(Quote, id)

    else:
        if not name:
            print(
                f"Please provide the name of the {entity_type} to delete using --name."
            )

            return

        if entity_type == "brand":
            entity = Brand.by_name(session, name)

        elif entity_type == "product":
            entity = Product.by_name(session, name)

        elif entity_type == "vendor":
            entity = Vendor.by_name(session, name)

    if not entity:
        print(f"{entity_type.capitalize()} not found.")

        return

    confirm = input(
        f"Are you sure you want to delete {entity_type} '{entity.name if name else entity.id}'? (y/n): "
    )

    if confirm.lower() == "y":
        session.delete(entity)

        session.commit()

        print(f"Deleted {entity_type}: '{entity.name if name else entity.id}'")


def update_entity(session, entity_type, name, new_name):
    """Update an entity's name"""

    if entity_type == "brand":
        entity = Brand.by_name(session, name)

    elif entity_type == "product":
        entity = Product.by_name(session, name)

    elif entity_type == "vendor":
        entity = Vendor.by_name(session, name)

    else:
        print(f"Updating '{entity_type}' is not supported.")

        return

    if not entity:
        print(f"{entity_type.capitalize()} '{name}' not found.")

        return

    if new_name:
        entity.name = new_name

        session.commit()

        print(f"Updated {entity_type} '{name}' to '{new_name}'.")


def seed_database(session):
    """Populate database with sample data"""
    import datetime

    # Brands
    brands_data = [
        "Apple",
        "Samsung",
        "Sony",
        "LG",
        "Dell",
        "HP",
        "Lenovo",
        "Asus",
        "Acer",
        "Microsoft",
    ]
    brands = {}
    for name in brands_data:
        existing = Brand.by_name(session, name)
        if existing:
            brands[name] = existing
        else:
            brand = Brand(name=name)
            session.add(brand)
            brands[name] = brand
    session.commit()
    print(f"Added {len(brands_data)} brands")

    # Products (brand, name, category)
    products_data = [
        ("Apple", "iPhone 15 Pro", "Mobile Phones"),
        ("Apple", "MacBook Air M3", "Laptops"),
        ("Apple", "iPad Pro 12.9", "Tablets"),
        ("Samsung", "Galaxy S24 Ultra", "Mobile Phones"),
        ("Samsung", "Galaxy Tab S9", "Tablets"),
        ("Sony", "WH-1000XM5", "Headphones"),
        ("Sony", "PlayStation 5", "Gaming Consoles"),
        ("LG", "C3 OLED 65", "TVs"),
        ("Dell", "XPS 15", "Laptops"),
        ("HP", "Spectre x360", "Laptops"),
        ("Lenovo", "ThinkPad X1 Carbon", "Laptops"),
        ("Asus", "ROG Zephyrus G14", "Laptops"),
        ("Microsoft", "Surface Pro 9", "Tablets"),
        ("Microsoft", "Xbox Series X", "Gaming Consoles"),
    ]
    products = {}
    for brand_name, product_name, category in products_data:
        existing = Product.by_name(session, product_name)
        if existing:
            existing.category = category  # Update category if exists
            products[product_name] = existing
        else:
            product = Product(
                name=product_name, brand=brands[brand_name], category=category
            )
            session.add(product)
            products[product_name] = product
    session.commit()
    print(f"Added {len(products_data)} products")

    # Vendors
    vendors_data = [
        ("Amazon US", "USD", None, 0.0),
        ("Amazon UK", "GBP", "UKPRIME", 5.0),
        ("Amazon DE", "EUR", None, 0.0),
        ("Best Buy", "USD", "BBY10", 10.0),
        ("B&H Photo", "USD", None, 0.0),
        ("Newegg", "USD", "NEWEGG5", 5.0),
        ("Adorama", "USD", None, 0.0),
        ("Currys UK", "GBP", None, 0.0),
        ("MediaMarkt", "EUR", "MM15", 15.0),
    ]
    vendors = {}
    for name, currency, discount_code, discount in vendors_data:
        existing = Vendor.by_name(session, name)
        if existing:
            vendors[name] = existing
        else:
            vendor = Vendor(
                name=name,
                currency=currency,
                discount_code=discount_code,
                discount=discount,
            )
            session.add(vendor)
            vendors[name] = vendor
    session.commit()
    print(f"Added {len(vendors_data)} vendors")

    # Forex rates
    today = datetime.date.today()
    forex_data = [
        ("EUR", 1.08),
        ("GBP", 1.27),
        ("JPY", 0.0067),
        ("CAD", 0.74),
        ("AUD", 0.65),
    ]
    for code, rate in forex_data:
        existing = session.execute(
            select(Forex).where(Forex.code == code, Forex.date == today)
        ).scalar_one_or_none()
        if not existing:
            fx = Forex(code=code, usd_per_unit=rate, date=today)
            session.add(fx)
    session.commit()
    print(f"Added {len(forex_data)} forex rates")

    # Quotes
    quotes_data = [
        ("Amazon US", "iPhone 15 Pro", 999.00),
        ("Best Buy", "iPhone 15 Pro", 999.00),
        ("B&H Photo", "iPhone 15 Pro", 979.00),
        ("Amazon US", "MacBook Air M3", 1099.00),
        ("Best Buy", "MacBook Air M3", 1099.00),
        ("Amazon US", "Galaxy S24 Ultra", 1299.00),
        ("Newegg", "Galaxy S24 Ultra", 1249.00),
        ("Amazon US", "WH-1000XM5", 348.00),
        ("Amazon UK", "WH-1000XM5", 279.00),
        ("Amazon DE", "WH-1000XM5", 299.00),
        ("Best Buy", "PlayStation 5", 499.00),
        ("Amazon US", "PlayStation 5", 499.00),
        ("Amazon US", "XPS 15", 1499.00),
        ("Dell", "XPS 15", 1399.00) if Vendor.by_name(session, "Dell") else None,
        ("Amazon US", "C3 OLED 65", 1499.00),
        ("Best Buy", "C3 OLED 65", 1399.00),
        ("Currys UK", "C3 OLED 65", 1199.00),
        ("Amazon US", "ThinkPad X1 Carbon", 1649.00),
        ("Newegg", "ThinkPad X1 Carbon", 1599.00),
        ("Amazon US", "Surface Pro 9", 999.00),
        ("Best Buy", "Surface Pro 9", 999.00),
        ("MediaMarkt", "Surface Pro 9", 949.00),
    ]
    quote_count = 0
    for item in quotes_data:
        if item is None:
            continue
        vendor_name, product_name, price = item
        vendor = vendors.get(vendor_name)
        product = products.get(product_name)
        if not vendor or not product:
            continue

        value = price
        original_value = None
        original_currency = None

        if vendor.currency != "USD":
            fx_rate = session.execute(
                select(Forex).where(Forex.code == vendor.currency)
            ).scalar_one_or_none()
            if fx_rate:
                original_value = value
                original_currency = vendor.currency
                value = value * fx_rate.usd_per_unit

        quote = Quote(
            vendor=vendor,
            product=product,
            currency="USD",
            value=value,
            original_value=original_value,
            original_currency=original_currency,
        )
        session.add(quote)
        quote_count += 1
    session.commit()
    print(f"Added {quote_count} quotes")
    print("Database seeded successfully!")


def search_entities(session, query):
    """Search for items in the database"""

    print(f"Searching for '{query}'...")

    brands = (
        session.execute(select(Brand).where(Brand.name.ilike(f"%{query}%")))
        .scalars()
        .all()
    )

    products = (
        session.execute(select(Product).where(Product.name.ilike(f"%{query}%")))
        .scalars()
        .all()
    )

    vendors = (
        session.execute(select(Vendor).where(Vendor.name.ilike(f"%{query}%")))
        .scalars()
        .all()
    )

    if brands:
        print("\n--- Brands ---")

        headers = ["ID", "Name", "Products"]

        data = [[b.id, b.name, ", ".join([p.name for p in b.products])] for b in brands]

        print(tabulate(data, headers=headers, tablefmt="grid"))

    if products:
        print("\n--- Products ---")

        headers = ["ID", "Name", "Brand"]

        data = [[p.id, p.name, p.brand.name] for p in products]

        print(tabulate(data, headers=headers, tablefmt="grid"))

    if vendors:
        print("\n--- Vendors ---")

        headers = ["ID", "Name", "Currency", "Quotes"]

        data = [[v.id, v.name, v.currency, len(v.quotes)] for v in vendors]

        print(tabulate(data, headers=headers, tablefmt="grid"))


def main():
    parser = argparse.ArgumentParser(
        description="Buyer - Purchasing support and vendor quote management"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add entities")
    opt = add_parser.add_argument
    opt("-b", "--brand", type=str, help="Add a brand")
    opt("-p", "--product", type=str, help="Add a product (requires --brand)")
    opt("-v", "--vendor", type=str, help="Add a vendor")
    opt(
        "-q",
        "--quote",
        type=float,
        help="Add a quote (requires --vendor and --product)",
    )
    opt(
        "-c",
        "--currency",
        type=str,
        default="USD",
        help="Currency for vendor (default: USD)",
    )
    opt("-dc", "--discount-code", type=str, help="Discount code for vendor")
    opt(
        "-d",
        "--discount",
        type=float,
        default=0.0,
        help="Discount percentage for vendor",
    )
    opt(
        "--shipping",
        type=float,
        help="Shipping cost for quote",
    )
    opt(
        "--tax-rate",
        type=float,
        help="Tax rate percentage for quote",
    )

    # Add-fx command
    add_fx_parser = subparsers.add_parser("add-fx", help="Add forex rates")
    opt = add_fx_parser.add_argument
    opt("--code", type=str, required=True, help="Currency code (e.g., EUR, GBP)")
    opt(
        "--usd-per-unit",
        type=float,
        required=True,
        help="USD per unit (e.g., 1.085 for EUR)",
    )
    opt("--date", type=str, help="Date for rate (YYYY-MM-DD, defaults to today)")

    # List command
    list_parser = subparsers.add_parser("list", help="List entities")
    list_parser.add_argument(
        "type",
        choices=["brands", "products", "vendors", "quotes"],
        help="Type of entity to list",
    )
    list_parser.add_argument("--filter", type=str, help="Filter by name")
    list_parser.add_argument("--sort-by", type=str, help="Sort by column")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete entities")
    opt = delete_parser.add_argument
    opt(
        "type",
        choices=["brand", "product", "vendor", "quote"],
        help="Type of entity to delete",
    )
    opt("--name", type=str, help="Name of the entity to delete")
    opt("--id", type=int, help="ID of the quote to delete")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update entities")
    opt = update_parser.add_argument
    opt("type", choices=["brand", "product", "vendor"], help="Type of entity to update")
    opt("name", type=str, help="Name of the entity to update")
    opt("--new-name", type=str, help="New name for the entity")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for items")
    search_parser.add_argument("query", type=str, help="Search query")

    # TUI command
    subparsers.add_parser("tui", help="Launch interactive TUI")

    # Seed command
    subparsers.add_parser("seed", help="Populate database with sample data")

    # Alert command
    alert_parser = subparsers.add_parser("alert", help="Manage price alerts")
    alert_subparsers = alert_parser.add_subparsers(
        dest="alert_command", help="Alert commands"
    )

    # Alert add
    alert_add_parser = alert_subparsers.add_parser("add", help="Add a price alert")
    alert_add_parser.add_argument("product", type=str, help="Product name")
    alert_add_parser.add_argument("threshold", type=float, help="Price threshold")

    # Alert list
    alert_list_parser = alert_subparsers.add_parser("list", help="List price alerts")
    alert_list_parser.add_argument(
        "--triggered", action="store_true", help="Show only triggered alerts"
    )

    # Alert deactivate
    alert_deactivate_parser = alert_subparsers.add_parser(
        "deactivate", help="Deactivate an alert"
    )
    alert_deactivate_parser.add_argument("id", type=int, help="Alert ID")

    # History command
    history_parser = subparsers.add_parser("history", help="View price history")
    history_parser.add_argument("--product", type=str, help="Product name")
    history_parser.add_argument("--quote-id", type=int, help="Quote ID")

    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare prices")
    compare_parser.add_argument("--product", type=str, help="Exact product name")
    compare_parser.add_argument("--search", type=str, help="Search term for products")
    compare_parser.add_argument("--category", type=str, help="Product category")
    compare_parser.add_argument("--brand", type=str, help="Brand name")

    # Category command
    category_parser = subparsers.add_parser(
        "category", help="Manage product categories"
    )
    category_subparsers = category_parser.add_subparsers(
        dest="category_command", help="Category commands"
    )

    # Category set
    category_set_parser = category_subparsers.add_parser(
        "set", help="Set product category"
    )
    category_set_parser.add_argument("product", type=str, help="Product name")
    category_set_parser.add_argument("category", type=str, help="Category name")

    # Category list
    category_subparsers.add_parser("list", help="List all categories")

    # Purchase list command
    list_parser = subparsers.add_parser("purchase-list", help="Manage purchase lists")
    list_subparsers = list_parser.add_subparsers(
        dest="list_command", help="Purchase list commands"
    )

    # Purchase list create
    list_create_parser = list_subparsers.add_parser(
        "create", help="Create a purchase list"
    )
    list_create_parser.add_argument("name", type=str, help="List name")
    list_create_parser.add_argument("--description", type=str, help="List description")

    # Purchase list add quote
    list_add_parser = list_subparsers.add_parser("add", help="Add quote to list")
    list_add_parser.add_argument("list_name", type=str, help="Purchase list name")
    list_add_parser.add_argument("quote_id", type=int, help="Quote ID to add")

    # Purchase list remove quote
    list_remove_parser = list_subparsers.add_parser(
        "remove", help="Remove quote from list"
    )
    list_remove_parser.add_argument("list_name", type=str, help="Purchase list name")
    list_remove_parser.add_argument("quote_id", type=int, help="Quote ID to remove")

    # Purchase list show
    list_show_parser = list_subparsers.add_parser(
        "show", help="Show purchase list contents"
    )
    list_show_parser.add_argument("name", type=str, help="List name")

    # Purchase list delete
    list_delete_parser = list_subparsers.add_parser(
        "delete", help="Delete a purchase list"
    )
    list_delete_parser.add_argument("name", type=str, help="List name")

    # Purchase list all
    list_subparsers.add_parser("all", help="List all purchase lists")

    # Status command
    status_parser = subparsers.add_parser("status", help="Manage quote status")
    status_subparsers = status_parser.add_subparsers(
        dest="status_command", help="Status commands"
    )

    # Status set
    status_set_parser = status_subparsers.add_parser("set", help="Set quote status")
    status_set_parser.add_argument("quote_id", type=int, help="Quote ID")
    status_set_parser.add_argument(
        "status",
        type=str,
        choices=["considering", "ordered", "received"],
        help="Status",
    )

    # Status list
    status_list_parser = status_subparsers.add_parser(
        "list", help="List quotes by status"
    )
    status_list_parser.add_argument(
        "status",
        type=str,
        choices=["considering", "ordered", "received"],
        help="Status",
    )

    # Note command
    note_parser = subparsers.add_parser("note", help="Manage notes")
    note_subparsers = note_parser.add_subparsers(
        dest="note_command", help="Note commands"
    )

    # Note add
    note_add_parser = note_subparsers.add_parser("add", help="Add a note")
    note_add_parser.add_argument(
        "entity_type",
        type=str,
        choices=["product", "vendor", "quote", "brand"],
        help="Entity type",
    )
    note_add_parser.add_argument("entity_id", type=int, help="Entity ID")
    note_add_parser.add_argument("content", type=str, help="Note content")

    # Note list
    note_list_parser = note_subparsers.add_parser("list", help="List notes for entity")
    note_list_parser.add_argument(
        "entity_type",
        type=str,
        choices=["product", "vendor", "quote", "brand"],
        help="Entity type",
    )
    note_list_parser.add_argument("entity_id", type=int, help="Entity ID")

    # Note delete
    note_delete_parser = note_subparsers.add_parser("delete", help="Delete a note")
    note_delete_parser.add_argument("note_id", type=int, help="Note ID")

    # Tag command
    tag_parser = subparsers.add_parser("tag", help="Manage tags")
    tag_subparsers = tag_parser.add_subparsers(dest="tag_command", help="Tag commands")

    # Tag add
    tag_add_parser = tag_subparsers.add_parser("add", help="Add tag to entity")
    tag_add_parser.add_argument("tag_name", type=str, help="Tag name")
    tag_add_parser.add_argument(
        "entity_type",
        type=str,
        choices=["product", "vendor", "quote", "brand"],
        help="Entity type",
    )
    tag_add_parser.add_argument("entity_id", type=int, help="Entity ID")

    # Tag remove
    tag_remove_parser = tag_subparsers.add_parser(
        "remove", help="Remove tag from entity"
    )
    tag_remove_parser.add_argument("tag_name", type=str, help="Tag name")
    tag_remove_parser.add_argument(
        "entity_type",
        type=str,
        choices=["product", "vendor", "quote", "brand"],
        help="Entity type",
    )
    tag_remove_parser.add_argument("entity_id", type=int, help="Entity ID")

    # Tag list
    tag_list_parser = tag_subparsers.add_parser("list", help="List tags")
    tag_list_parser.add_argument(
        "--entity-type",
        type=str,
        choices=["product", "vendor", "quote", "brand"],
        help="Filter by entity type",
    )
    tag_list_parser.add_argument(
        "--entity-id",
        type=int,
        help="Show tags for specific entity (requires --entity-type)",
    )

    # Tag search
    tag_search_parser = tag_subparsers.add_parser("search", help="Find entities by tag")
    tag_search_parser.add_argument("tag_name", type=str, help="Tag name")
    tag_search_parser.add_argument(
        "--entity-type",
        type=str,
        choices=["product", "vendor", "quote", "brand"],
        help="Filter by entity type",
    )

    # Watchlist command
    watchlist_parser = subparsers.add_parser("watchlist", help="Manage watchlist")
    watchlist_subparsers = watchlist_parser.add_subparsers(
        dest="watchlist_command", help="Watchlist commands"
    )

    # Watchlist add
    watchlist_add_parser = watchlist_subparsers.add_parser(
        "add", help="Add product to watchlist"
    )
    watchlist_add_parser.add_argument("product", type=str, help="Product name")
    watchlist_add_parser.add_argument("--target-price", type=float, help="Target price")
    watchlist_add_parser.add_argument("--notes", type=str, help="Notes")

    # Watchlist list
    watchlist_list_parser = watchlist_subparsers.add_parser(
        "list", help="List watchlist"
    )
    watchlist_list_parser.add_argument(
        "--all", action="store_true", help="Include inactive items"
    )

    # Watchlist update
    watchlist_update_parser = watchlist_subparsers.add_parser(
        "update", help="Update watchlist entry"
    )
    watchlist_update_parser.add_argument("id", type=int, help="Watchlist entry ID")
    watchlist_update_parser.add_argument(
        "--target-price", type=float, help="New target price"
    )
    watchlist_update_parser.add_argument("--notes", type=str, help="New notes")

    # Watchlist remove
    watchlist_remove_parser = watchlist_subparsers.add_parser(
        "remove", help="Remove from watchlist"
    )
    watchlist_remove_parser.add_argument("id", type=int, help="Watchlist entry ID")

    # Import command
    import_parser = subparsers.add_parser("import", help="Import data from files")
    import_subparsers = import_parser.add_subparsers(
        dest="import_command", help="Import commands"
    )

    # Import quotes
    import_quotes_parser = import_subparsers.add_parser(
        "quotes", help="Import quotes from CSV/JSON"
    )
    import_quotes_parser.add_argument("file", type=str, help="Path to CSV or JSON file")
    import_quotes_parser.add_argument(
        "--no-create", action="store_true", help="Don't create missing vendors/products"
    )

    # Export command
    export_parser = subparsers.add_parser("export", help="Export data to files")
    export_subparsers = export_parser.add_subparsers(
        dest="export_command", help="Export commands"
    )

    # Export quotes
    export_quotes_parser = export_subparsers.add_parser("quotes", help="Export quotes")
    export_quotes_parser.add_argument("--file", type=str, help="Output file path")
    export_quotes_parser.add_argument(
        "--format",
        type=str,
        choices=["csv", "markdown"],
        default="csv",
        help="Output format",
    )
    export_quotes_parser.add_argument(
        "--filter", type=str, help="Filter by product name"
    )

    # Export products
    export_products_parser = export_subparsers.add_parser(
        "products", help="Export products to CSV"
    )
    export_products_parser.add_argument("--file", type=str, help="Output file path")

    # Export vendors
    export_vendors_parser = export_subparsers.add_parser(
        "vendors", help="Export vendors to CSV"
    )
    export_vendors_parser.add_argument("--file", type=str, help="Output file path")

    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Backup the database")
    backup_parser.add_argument(
        "--output", type=str, help="Backup file path (default: auto-generated)"
    )

    # Restore command
    restore_parser = subparsers.add_parser(
        "restore", help="Restore database from backup"
    )
    restore_parser.add_argument("backup_file", type=str, help="Path to backup file")
    restore_parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Don't backup current database before restore",
    )

    # Backups command (list backups)
    subparsers.add_parser("backups", help="List available backups")

    # Duplicates command
    duplicates_parser = subparsers.add_parser(
        "duplicates", help="Find and manage duplicate entities"
    )
    duplicates_subparsers = duplicates_parser.add_subparsers(
        dest="duplicates_command", help="Duplicates commands"
    )

    # Find duplicate vendors
    dup_vendors_parser = duplicates_subparsers.add_parser(
        "vendors", help="Find similar vendors"
    )
    dup_vendors_parser.add_argument(
        "--threshold", type=float, default=0.8, help="Similarity threshold (0-1)"
    )

    # Find duplicate products
    dup_products_parser = duplicates_subparsers.add_parser(
        "products", help="Find similar products"
    )
    dup_products_parser.add_argument(
        "--threshold", type=float, default=0.8, help="Similarity threshold (0-1)"
    )

    # Merge vendors
    merge_vendors_parser = duplicates_subparsers.add_parser(
        "merge-vendors", help="Merge vendors"
    )
    merge_vendors_parser.add_argument("keep_id", type=int, help="ID of vendor to keep")
    merge_vendors_parser.add_argument(
        "merge_ids", type=int, nargs="+", help="IDs of vendors to merge"
    )

    # Merge products
    merge_products_parser = duplicates_subparsers.add_parser(
        "merge-products", help="Merge products"
    )
    merge_products_parser.add_argument(
        "keep_id", type=int, help="ID of product to keep"
    )
    merge_products_parser.add_argument(
        "merge_ids", type=int, nargs="+", help="IDs of products to merge"
    )

    # Clipboard command
    clipboard_parser = subparsers.add_parser("clipboard", help="Copy data to clipboard")
    clipboard_subparsers = clipboard_parser.add_subparsers(
        dest="clipboard_command", help="Clipboard commands"
    )

    # Clipboard copy quote
    clip_quote_parser = clipboard_subparsers.add_parser(
        "quote", help="Copy quote to clipboard"
    )
    clip_quote_parser.add_argument("quote_id", type=int, help="Quote ID")

    # Clipboard copy product
    clip_product_parser = clipboard_subparsers.add_parser(
        "product", help="Copy product to clipboard"
    )
    clip_product_parser.add_argument("product_name", type=str, help="Product name")

    # Clipboard copy vendor
    clip_vendor_parser = clipboard_subparsers.add_parser(
        "vendor", help="Copy vendor to clipboard"
    )
    clip_vendor_parser.add_argument("vendor_name", type=str, help="Vendor name")

    # Vendor URL command
    vendor_url_parser = subparsers.add_parser("vendor-url", help="Manage vendor URLs")
    vendor_url_subparsers = vendor_url_parser.add_subparsers(
        dest="vendor_url_command", help="Vendor URL commands"
    )

    # Vendor URL set
    url_set_parser = vendor_url_subparsers.add_parser("set", help="Set vendor URL")
    url_set_parser.add_argument("vendor", type=str, help="Vendor name")
    url_set_parser.add_argument("url", type=str, help="URL to set")

    # Vendor URL open
    url_open_parser = vendor_url_subparsers.add_parser(
        "open", help="Open vendor URL in browser"
    )
    url_open_parser.add_argument("vendor", type=str, help="Vendor name")

    # Vendor URL clear
    url_clear_parser = vendor_url_subparsers.add_parser(
        "clear", help="Clear vendor URL"
    )
    url_clear_parser.add_argument("vendor", type=str, help="Vendor name")

    # Receipt command
    receipt_parser = subparsers.add_parser("receipt", help="Manage receipt attachments")
    receipt_subparsers = receipt_parser.add_subparsers(
        dest="receipt_command", help="Receipt commands"
    )

    # Receipt attach
    receipt_attach_parser = receipt_subparsers.add_parser(
        "attach", help="Attach receipt to quote"
    )
    receipt_attach_parser.add_argument("quote_id", type=int, help="Quote ID")
    receipt_attach_parser.add_argument(
        "file_path", type=str, help="Path to receipt file"
    )

    # Receipt open
    receipt_open_parser = receipt_subparsers.add_parser(
        "open", help="Open receipt file"
    )
    receipt_open_parser.add_argument("quote_id", type=int, help="Quote ID")

    # Receipt detach
    receipt_detach_parser = receipt_subparsers.add_parser(
        "detach", help="Remove receipt from quote"
    )
    receipt_detach_parser.add_argument("quote_id", type=int, help="Quote ID")

    # Receipt list
    receipt_subparsers.add_parser("list", help="List quotes with receipts")

    # Scrape command
    scrape_parser = subparsers.add_parser(
        "scrape", help="Scrape product prices from URLs"
    )
    scrape_subparsers = scrape_parser.add_subparsers(
        dest="scrape_command", help="Scrape commands"
    )

    # Scrape URL
    scrape_url_parser = scrape_subparsers.add_parser(
        "url", help="Scrape price from URL"
    )
    scrape_url_parser.add_argument("url", type=str, help="URL to scrape")

    # Scrape and create quote
    scrape_quote_parser = scrape_subparsers.add_parser(
        "quote", help="Create quote from scraped URL"
    )
    scrape_quote_parser.add_argument("url", type=str, help="URL to scrape")
    scrape_quote_parser.add_argument(
        "--vendor", type=str, required=True, help="Vendor name"
    )
    scrape_quote_parser.add_argument(
        "--product", type=str, required=True, help="Product name"
    )
    scrape_quote_parser.add_argument(
        "--brand", type=str, help="Brand name (for new products)"
    )

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate HTML reports")
    report_subparsers = report_parser.add_subparsers(
        dest="report_command", help="Report commands"
    )

    # Report price-comparison
    report_price_parser = report_subparsers.add_parser(
        "price-comparison", help="Compare prices across vendors"
    )
    report_price_parser.add_argument(
        "--filter", type=str, help="Filter products by name"
    )
    report_price_parser.add_argument(
        "--output", type=str, help="Output HTML file path"
    )

    # Report purchase-summary
    report_purchase_parser = report_subparsers.add_parser(
        "purchase-summary", help="Summary of quotes by status"
    )
    report_purchase_parser.add_argument(
        "--output", type=str, help="Output HTML file path"
    )

    # Report vendor-analysis
    report_vendor_parser = report_subparsers.add_parser(
        "vendor-analysis", help="Vendor statistics and analysis"
    )
    report_vendor_parser.add_argument(
        "--output", type=str, help="Output HTML file path"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    session = Session()

    try:
        if args.command == "add":
            if args.brand and not args.product and not args.vendor:
                # Add brand only
                add_brand(session, args.brand)

            elif args.brand and args.product and not args.vendor:
                # Add product under brand
                add_product(session, args.brand, args.product)

            elif args.vendor and not args.product:
                # Add vendor only
                add_vendor(
                    session,
                    args.vendor,
                    args.currency,
                    args.discount_code,
                    args.discount,
                )

            elif args.vendor and args.product and args.quote is not None:
                # Add quote
                add_quote(
                    session,
                    args.vendor,
                    args.product,
                    args.quote,
                    args.brand,
                    getattr(args, "shipping", None),
                    getattr(args, "tax_rate", None),
                )

            else:
                print("Invalid combination of arguments for 'add' command")
                add_parser.print_help()

        elif args.command == "add-fx":
            add_fx(
                session,
                args.code,
                args.usd_per_unit,
                args.date if hasattr(args, "date") else None,
            )

        elif args.command == "list":
            list_entities(session, args.type, args.filter, args.sort_by)

        elif args.command == "delete":
            delete_entity(session, args.type, args.name, args.id)

        elif args.command == "update":
            update_entity(session, args.type, args.name, args.new_name)

        elif args.command == "search":
            search_entities(session, args.query)

        elif args.command == "tui":
            session.close()
            from .tui import main as tui_main

            tui_main()
            return

        elif args.command == "seed":
            seed_database(session)

        elif args.command == "alert":
            from .services import PriceAlertService, NotFoundError, ValidationError

            if args.alert_command == "add":
                try:
                    alert = PriceAlertService.create(
                        session, args.product, args.threshold
                    )
                    print(
                        f"Created alert #{alert.id} for '{args.product}' at ${args.threshold:.2f}"
                    )
                except NotFoundError as e:
                    print(f"Error: {e}")
                except ValidationError as e:
                    print(f"Error: {e}")

            elif args.alert_command == "list":
                if args.triggered:
                    alerts = PriceAlertService.get_triggered(session)
                    if not alerts:
                        print("No triggered alerts")
                        return
                    headers = ["ID", "Product", "Threshold", "Triggered At"]
                    data = [
                        [
                            a.id,
                            a.product.name,
                            f"${a.threshold_value:.2f}",
                            str(a.triggered_at),
                        ]
                        for a in alerts
                    ]
                else:
                    alerts = PriceAlertService.get_all(session)
                    if not alerts:
                        print("No alerts")
                        return
                    headers = ["ID", "Product", "Threshold", "Status", "Triggered At"]
                    data = [
                        [
                            a.id,
                            a.product.name,
                            f"${a.threshold_value:.2f}",
                            "Active" if a.active else "Inactive",
                            str(a.triggered_at) if a.triggered_at else "-",
                        ]
                        for a in alerts
                    ]
                print(tabulate(data, headers=headers, tablefmt="grid"))

            elif args.alert_command == "deactivate":
                try:
                    alert = PriceAlertService.deactivate(session, args.id)
                    print(f"Deactivated alert #{alert.id}")
                except NotFoundError as e:
                    print(f"Error: {e}")

            else:
                print("Usage: buylog alert [add|list|deactivate]")

        elif args.command == "history":
            from .services import QuoteHistoryService, QuoteService

            if args.quote_id:
                history = QuoteHistoryService.get_history(session, args.quote_id)
                if not history:
                    print(f"No history for quote #{args.quote_id}")
                    return
                headers = ["Date", "Old Price", "New Price", "Type"]
                data = [
                    [
                        str(h.changed_at),
                        f"${h.old_value:.2f}" if h.old_value else "-",
                        f"${h.new_value:.2f}",
                        h.change_type,
                    ]
                    for h in history
                ]
                print(f"Price history for Quote #{args.quote_id}:")
                print(tabulate(data, headers=headers, tablefmt="grid"))

            elif args.product:
                product = Product.by_name(session, args.product)
                if not product:
                    print(f"Product '{args.product}' not found")
                    return
                history = QuoteHistoryService.get_product_history(session, product.id)
                if not history:
                    print(f"No history for product '{args.product}'")
                    return
                headers = ["Date", "Quote ID", "Old Price", "New Price", "Type"]
                data = [
                    [
                        str(h.changed_at),
                        h.quote_id,
                        f"${h.old_value:.2f}" if h.old_value else "-",
                        f"${h.new_value:.2f}",
                        h.change_type,
                    ]
                    for h in history
                ]
                print(f"Price history for '{args.product}':")
                print(tabulate(data, headers=headers, tablefmt="grid"))

            else:
                print("Usage: buylog history [--product NAME | --quote-id ID]")

        elif args.command == "compare":
            from .services import ComparisonService, NotFoundError

            def print_comparison(comparison: dict) -> None:
                """Print a single product comparison."""
                product = comparison["product"]
                quotes = comparison["quotes"]

                print(f"\n{product.brand.name} {product.name}")
                if product.category:
                    print(f"  Category: {product.category}")
                print("-" * 60)

                if not quotes:
                    print("  No quotes available")
                    return

                headers = ["Vendor", "Price", "Total", "Discount", "Shipping"]
                data = [
                    [
                        q.vendor.name,
                        f"${q.value:.2f}",
                        f"${q.total_cost:.2f}",
                        f"{q.discount}%" if q.discount else "-",
                        f"${q.shipping_cost:.2f}" if q.shipping_cost else "-",
                    ]
                    for q in quotes
                ]
                print(tabulate(data, headers=headers, tablefmt="simple"))

                print(f"\n  Best Price:  ${comparison['best_price']:.2f}")
                print(f"  Worst Price: ${comparison['worst_price']:.2f}")
                print(f"  Avg Price:   ${comparison['avg_price']:.2f}")
                print(
                    f"  Savings:     ${comparison['savings']:.2f} ({comparison['num_vendors']} vendors)"
                )

            try:
                if args.product:
                    result = ComparisonService.compare_product(session, args.product)
                    print_comparison(result)

                elif args.search:
                    result = ComparisonService.compare_by_search(session, args.search)
                    print(
                        f"Found {result['total_products']} products matching '{args.search}':"
                    )
                    for comp in result["products"]:
                        print_comparison(comp)

                elif args.category:
                    result = ComparisonService.compare_by_category(
                        session, args.category
                    )
                    print(
                        f"Found {result['total_products']} products in category '{args.category}':"
                    )
                    for comp in result["products"]:
                        print_comparison(comp)

                elif args.brand:
                    result = ComparisonService.compare_by_brand(session, args.brand)
                    print(
                        f"Found {result['total_products']} products from '{args.brand}':"
                    )
                    for comp in result["products"]:
                        print_comparison(comp)

                else:
                    print(
                        "Usage: buylog compare [--product NAME | --search TERM | --category CAT | --brand NAME]"
                    )

            except NotFoundError as e:
                print(f"Error: {e}")

        elif args.command == "category":
            from .services import ComparisonService, NotFoundError

            if args.category_command == "set":
                try:
                    product = ComparisonService.set_product_category(
                        session, args.product, args.category
                    )
                    print(
                        f"Set category '{args.category}' for product '{args.product}'"
                    )
                except NotFoundError as e:
                    print(f"Error: {e}")

            elif args.category_command == "list":
                categories = ComparisonService.get_categories(session)
                if categories:
                    print("Product Categories:")
                    for cat in categories:
                        # Count products in category
                        count = (
                            session.execute(
                                select(Product).where(Product.category == cat)
                            )
                            .scalars()
                            .all()
                        )
                        print(f"  - {cat} ({len(count)} products)")
                else:
                    print(
                        "No categories defined. Use 'buylog category set <product> <category>' to add one."
                    )

            else:
                print("Usage: buylog category [set|list]")

        elif args.command == "purchase-list":
            from .services import (
                PurchaseListService,
                NotFoundError,
                DuplicateError,
                ValidationError,
            )

            if args.list_command == "create":
                try:
                    plist = PurchaseListService.create(
                        session, args.name, getattr(args, "description", None)
                    )
                    print(f"Created purchase list '{plist.name}'")
                except DuplicateError as e:
                    print(f"Error: {e}")
                except ValidationError as e:
                    print(f"Error: {e}")

            elif args.list_command == "add":
                try:
                    plist = PurchaseListService.add_quote(
                        session, args.list_name, args.quote_id
                    )
                    print(f"Added quote #{args.quote_id} to list '{args.list_name}'")
                except (NotFoundError, DuplicateError) as e:
                    print(f"Error: {e}")

            elif args.list_command == "remove":
                try:
                    plist = PurchaseListService.remove_quote(
                        session, args.list_name, args.quote_id
                    )
                    print(
                        f"Removed quote #{args.quote_id} from list '{args.list_name}'"
                    )
                except NotFoundError as e:
                    print(f"Error: {e}")

            elif args.list_command == "show":
                plist = PurchaseListService.get_by_name(session, args.name)
                if not plist:
                    print(f"Purchase list '{args.name}' not found")
                    return
                print(f"Purchase List: {plist.name}")
                if plist.description:
                    print(f"Description: {plist.description}")
                print(f"Created: {plist.created_at}")
                print(f"Total Value: ${plist.total_value:.2f}")
                print("-" * 60)
                if plist.quotes:
                    headers = ["ID", "Vendor", "Product", "Price", "Status"]
                    data = [
                        [
                            q.id,
                            q.vendor.name,
                            f"{q.product.brand.name} {q.product.name}",
                            f"${q.total_cost:.2f}",
                            q.status or "-",
                        ]
                        for q in plist.quotes
                    ]
                    print(tabulate(data, headers=headers, tablefmt="grid"))
                else:
                    print("  No quotes in list")

            elif args.list_command == "delete":
                try:
                    PurchaseListService.delete(session, args.name)
                    print(f"Deleted purchase list '{args.name}'")
                except NotFoundError as e:
                    print(f"Error: {e}")

            elif args.list_command == "all":
                plists = PurchaseListService.get_all(session)
                if not plists:
                    print("No purchase lists")
                    return
                headers = ["Name", "Description", "Quotes", "Total"]
                data = [
                    [
                        p.name,
                        p.description or "-",
                        len(p.quotes),
                        f"${p.total_value:.2f}",
                    ]
                    for p in plists
                ]
                print(tabulate(data, headers=headers, tablefmt="grid"))

            else:
                print("Usage: buylog purchase-list [create|add|remove|show|delete|all]")

        elif args.command == "status":
            from .services import QuoteService, NotFoundError, ValidationError

            if args.status_command == "set":
                try:
                    quote = QuoteService.set_status(session, args.quote_id, args.status)
                    print(f"Set status '{args.status}' for quote #{args.quote_id}")
                except (NotFoundError, ValidationError) as e:
                    print(f"Error: {e}")

            elif args.status_command == "list":
                try:
                    quotes = QuoteService.get_by_status(session, args.status)
                    if not quotes:
                        print(f"No quotes with status '{args.status}'")
                        return
                    headers = ["ID", "Vendor", "Product", "Price", "Status"]
                    data = [
                        [
                            q.id,
                            q.vendor.name,
                            f"{q.product.brand.name} {q.product.name}",
                            f"${q.total_cost:.2f}",
                            q.status,
                        ]
                        for q in quotes
                    ]
                    print(f"Quotes with status '{args.status}':")
                    print(tabulate(data, headers=headers, tablefmt="grid"))
                except ValidationError as e:
                    print(f"Error: {e}")

            else:
                print("Usage: buylog status [set|list]")

        elif args.command == "note":
            from .services import NoteService, NotFoundError, ValidationError

            if args.note_command == "add":
                try:
                    note = NoteService.create(
                        session, args.entity_type, args.entity_id, args.content
                    )
                    print(
                        f"Added note #{note.id} to {args.entity_type}:{args.entity_id}"
                    )
                except ValidationError as e:
                    print(f"Error: {e}")

            elif args.note_command == "list":
                notes = NoteService.get_for_entity(
                    session, args.entity_type, args.entity_id
                )
                if not notes:
                    print(f"No notes for {args.entity_type}:{args.entity_id}")
                    return
                print(f"Notes for {args.entity_type}:{args.entity_id}:")
                for note in notes:
                    print(f"\n#{note.id} ({note.created_at}):")
                    print(f"  {note.content}")

            elif args.note_command == "delete":
                try:
                    NoteService.delete(session, args.note_id)
                    print(f"Deleted note #{args.note_id}")
                except NotFoundError as e:
                    print(f"Error: {e}")

            else:
                print("Usage: buylog note [add|list|delete]")

        elif args.command == "tag":
            from .services import TagService, NotFoundError, DuplicateError

            if args.tag_command == "add":
                try:
                    TagService.add_to_entity(
                        session, args.tag_name, args.entity_type, args.entity_id
                    )
                    print(
                        f"Added tag '{args.tag_name}' to {args.entity_type}:{args.entity_id}"
                    )
                except DuplicateError as e:
                    print(f"Error: {e}")

            elif args.tag_command == "remove":
                try:
                    TagService.remove_from_entity(
                        session, args.tag_name, args.entity_type, args.entity_id
                    )
                    print(
                        f"Removed tag '{args.tag_name}' from {args.entity_type}:{args.entity_id}"
                    )
                except NotFoundError as e:
                    print(f"Error: {e}")

            elif args.tag_command == "list":
                if args.entity_type and args.entity_id:
                    # List tags for specific entity
                    tags = TagService.get_for_entity(
                        session, args.entity_type, args.entity_id
                    )
                    if not tags:
                        print(f"No tags for {args.entity_type}:{args.entity_id}")
                        return
                    print(f"Tags for {args.entity_type}:{args.entity_id}:")
                    for tag in tags:
                        color_info = f" ({tag.color})" if tag.color else ""
                        print(f"  - {tag.name}{color_info}")
                else:
                    # List all tags
                    tags = TagService.get_all(session)
                    if not tags:
                        print("No tags")
                        return
                    headers = ["Name", "Color"]
                    data = [[t.name, t.color or "-"] for t in tags]
                    print(tabulate(data, headers=headers, tablefmt="grid"))

            elif args.tag_command == "search":
                try:
                    entity_tags = TagService.get_entities_by_tag(
                        session, args.tag_name, getattr(args, "entity_type", None)
                    )
                    if not entity_tags:
                        print(f"No entities with tag '{args.tag_name}'")
                        return
                    print(f"Entities with tag '{args.tag_name}':")
                    for et in entity_tags:
                        print(f"  - {et.entity_type}:{et.entity_id}")
                except NotFoundError as e:
                    print(f"Error: {e}")

            else:
                print("Usage: buylog tag [add|remove|list|search]")

        elif args.command == "watchlist":
            from .services import WatchlistService, NotFoundError, DuplicateError

            if args.watchlist_command == "add":
                try:
                    watchlist = WatchlistService.create(
                        session,
                        args.product,
                        getattr(args, "target_price", None),
                        getattr(args, "notes", None),
                    )
                    print(f"Added '{args.product}' to watchlist (ID: {watchlist.id})")
                except (NotFoundError, DuplicateError) as e:
                    print(f"Error: {e}")

            elif args.watchlist_command == "list":
                if getattr(args, "all", False):
                    items = WatchlistService.get_all(session)
                else:
                    items = WatchlistService.get_active(session)
                if not items:
                    print("Watchlist is empty")
                    return
                headers = ["ID", "Product", "Brand", "Target Price", "Notes", "Status"]
                data = [
                    [
                        w.id,
                        w.product.name,
                        w.product.brand.name,
                        f"${w.target_price:.2f}" if w.target_price else "-",
                        (w.notes[:30] + "...")
                        if w.notes and len(w.notes) > 30
                        else (w.notes or "-"),
                        "Active" if w.active else "Inactive",
                    ]
                    for w in items
                ]
                print(tabulate(data, headers=headers, tablefmt="grid"))

            elif args.watchlist_command == "update":
                try:
                    watchlist = WatchlistService.update(
                        session,
                        args.id,
                        getattr(args, "target_price", None),
                        getattr(args, "notes", None),
                    )
                    print(f"Updated watchlist entry #{args.id}")
                except NotFoundError as e:
                    print(f"Error: {e}")

            elif args.watchlist_command == "remove":
                try:
                    WatchlistService.delete(session, args.id)
                    print(f"Removed watchlist entry #{args.id}")
                except NotFoundError as e:
                    print(f"Error: {e}")

            else:
                print("Usage: buylog watchlist [add|list|update|remove]")

        elif args.command == "import":
            from .services import (
                ImportService,
                NotFoundError,
                ValidationError,
                ServiceError,
            )

            if args.import_command == "quotes":
                file_path = args.file
                create_missing = not getattr(args, "no_create", False)

                try:
                    # Detect format from extension
                    if file_path.endswith(".json"):
                        stats = ImportService.import_quotes_json(
                            session, file_path, create_missing
                        )
                    else:
                        stats = ImportService.import_quotes_csv(
                            session, file_path, create_missing
                        )

                    print("Import complete:")
                    print(f"  Imported: {stats['imported']}")
                    print(f"  Skipped: {stats['skipped']}")
                    if stats["created_vendors"]:
                        print(
                            f"  Created vendors: {', '.join(stats['created_vendors'])}"
                        )
                    if stats["created_products"]:
                        print(
                            f"  Created products: {', '.join(stats['created_products'])}"
                        )
                    if stats["errors"]:
                        print("  Errors:")
                        for err in stats["errors"][:10]:
                            print(f"    - {err}")
                        if len(stats["errors"]) > 10:
                            print(
                                f"    ... and {len(stats['errors']) - 10} more errors"
                            )
                except (NotFoundError, ValidationError, ServiceError) as e:
                    print(f"Error: {e}")

            else:
                print("Usage: buylog import quotes <file>")

        elif args.command == "export":
            from .services import ExportService

            if args.export_command == "quotes":
                file_path = getattr(args, "file", None)
                fmt = getattr(args, "format", "csv")
                filter_by = getattr(args, "filter", None)

                if fmt == "markdown":
                    result = ExportService.export_quotes_markdown(
                        session, file_path, filter_by
                    )
                else:
                    result = ExportService.export_quotes_csv(
                        session, file_path, filter_by
                    )

                if file_path:
                    print(f"Exported to: {result}")
                else:
                    print(result)

            elif args.export_command == "products":
                file_path = getattr(args, "file", None)
                result = ExportService.export_products_csv(session, file_path)
                if file_path:
                    print(f"Exported to: {result}")
                else:
                    print(result)

            elif args.export_command == "vendors":
                file_path = getattr(args, "file", None)
                result = ExportService.export_vendors_csv(session, file_path)
                if file_path:
                    print(f"Exported to: {result}")
                else:
                    print(result)

            else:
                print("Usage: buylog export [quotes|products|vendors]")

        elif args.command == "backup":
            from .services import BackupService
            from .config import Config

            db_path = Config.get_db_path()
            output = getattr(args, "output", None)

            try:
                backup_path = BackupService.backup(db_path, output)
                print(f"Backup created: {backup_path}")
            except Exception as e:
                print(f"Error: {e}")

        elif args.command == "restore":
            from .services import BackupService, NotFoundError
            from .config import Config

            backup_file = args.backup_file
            db_path = Config.get_db_path()
            create_backup = not getattr(args, "no_backup", False)

            try:
                session.close()  # Close current session before restore
                BackupService.restore(backup_file, db_path, create_backup)
                print(f"Database restored from: {backup_file}")
                if create_backup:
                    print("(Previous database was backed up)")
            except NotFoundError as e:
                print(f"Error: {e}")
            except Exception as e:
                print(f"Error: {e}")
            return  # Exit after restore

        elif args.command == "backups":
            from .services import BackupService
            from .config import Config

            db_path = Config.get_db_path()
            backups = BackupService.list_backups(db_path)

            if not backups:
                print("No backups found")
            else:
                print(f"Available backups ({len(backups)}):")
                for b in backups:
                    size_kb = b["size"] / 1024
                    print(f"  {b['name']} ({size_kb:.1f} KB) - {b['modified']}")

        elif args.command == "duplicates":
            from .services import DeduplicationService, NotFoundError

            if args.duplicates_command == "vendors":
                threshold = getattr(args, "threshold", 0.8)
                groups = DeduplicationService.find_similar_vendors(session, threshold)

                if not groups:
                    print("No similar vendors found")
                else:
                    print(f"Found {len(groups)} groups of similar vendors:")
                    for i, group in enumerate(groups, 1):
                        print(f"\nGroup {i}:")
                        for v in group:
                            print(f"  [{v.id}] {v.name} ({v.currency})")
                    print(
                        "\nTo merge: buylog duplicates merge-vendors <keep_id> <merge_id1> <merge_id2> ..."
                    )

            elif args.duplicates_command == "products":
                threshold = getattr(args, "threshold", 0.8)
                groups = DeduplicationService.find_similar_products(session, threshold)

                if not groups:
                    print("No similar products found")
                else:
                    print(f"Found {len(groups)} groups of similar products:")
                    for i, group in enumerate(groups, 1):
                        print(f"\nGroup {i}:")
                        for p in group:
                            print(f"  [{p.id}] {p.name} ({p.brand.name})")
                    print(
                        "\nTo merge: buylog duplicates merge-products <keep_id> <merge_id1> <merge_id2> ..."
                    )

            elif args.duplicates_command == "merge-vendors":
                try:
                    vendor = DeduplicationService.merge_vendors(
                        session, args.keep_id, args.merge_ids
                    )
                    print(f"Merged vendors into: [{vendor.id}] {vendor.name}")
                except NotFoundError as e:
                    print(f"Error: {e}")

            elif args.duplicates_command == "merge-products":
                try:
                    product = DeduplicationService.merge_products(
                        session, args.keep_id, args.merge_ids
                    )
                    print(f"Merged products into: [{product.id}] {product.name}")
                except NotFoundError as e:
                    print(f"Error: {e}")

            else:
                print(
                    "Usage: buylog duplicates [vendors|products|merge-vendors|merge-products]"
                )

        elif args.command == "clipboard":
            from .services import ClipboardService, NotFoundError, ServiceError

            if args.clipboard_command == "quote":
                try:
                    text = ClipboardService.copy_quote(session, args.quote_id)
                    print(f"Copied quote #{args.quote_id} to clipboard:")
                    print(text)
                except (NotFoundError, ServiceError) as e:
                    print(f"Error: {e}")

            elif args.clipboard_command == "product":
                try:
                    text = ClipboardService.copy_product(session, args.product_name)
                    print(f"Copied product '{args.product_name}' to clipboard:")
                    print(text)
                except (NotFoundError, ServiceError) as e:
                    print(f"Error: {e}")

            elif args.clipboard_command == "vendor":
                try:
                    text = ClipboardService.copy_vendor(session, args.vendor_name)
                    print(f"Copied vendor '{args.vendor_name}' to clipboard:")
                    print(text)
                except (NotFoundError, ServiceError) as e:
                    print(f"Error: {e}")

            else:
                print("Usage: buylog clipboard [quote|product|vendor]")

        elif args.command == "vendor-url":
            from .services import (
                VendorURLService,
                NotFoundError,
                ValidationError,
                ServiceError,
            )

            if args.vendor_url_command == "set":
                try:
                    vendor = VendorURLService.set_url(session, args.vendor, args.url)
                    print(f"Set URL for '{args.vendor}': {args.url}")
                except (NotFoundError, ValidationError, ServiceError) as e:
                    print(f"Error: {e}")

            elif args.vendor_url_command == "open":
                try:
                    url = VendorURLService.open_url(session, args.vendor)
                    print(f"Opening URL: {url}")
                except (NotFoundError, ValidationError, ServiceError) as e:
                    print(f"Error: {e}")

            elif args.vendor_url_command == "clear":
                try:
                    vendor = VendorURLService.clear_url(session, args.vendor)
                    print(f"Cleared URL for '{args.vendor}'")
                except (NotFoundError, ServiceError) as e:
                    print(f"Error: {e}")

            else:
                print("Usage: buylog vendor-url [set|open|clear]")

        elif args.command == "receipt":
            from .services import (
                ReceiptService,
                NotFoundError,
                ValidationError,
                ServiceError,
            )

            if args.receipt_command == "attach":
                try:
                    quote = ReceiptService.attach(
                        session, args.quote_id, args.file_path
                    )
                    print(
                        f"Attached receipt to quote #{args.quote_id}: {args.file_path}"
                    )
                except (NotFoundError, ServiceError) as e:
                    print(f"Error: {e}")

            elif args.receipt_command == "open":
                try:
                    path = ReceiptService.open(session, args.quote_id)
                    print(f"Opening receipt: {path}")
                except (NotFoundError, ValidationError, ServiceError) as e:
                    print(f"Error: {e}")

            elif args.receipt_command == "detach":
                try:
                    quote = ReceiptService.detach(session, args.quote_id)
                    print(f"Detached receipt from quote #{args.quote_id}")
                except (NotFoundError, ServiceError) as e:
                    print(f"Error: {e}")

            elif args.receipt_command == "list":
                quotes = ReceiptService.get_quotes_with_receipts(session)
                if not quotes:
                    print("No quotes with receipts attached")
                else:
                    headers = ["ID", "Vendor", "Product", "Price", "Receipt"]
                    data = [
                        [
                            q.id,
                            q.vendor.name,
                            f"{q.product.brand.name} {q.product.name}",
                            f"${q.total_cost:.2f}",
                            Path(q.receipt_path).name if q.receipt_path else "-",
                        ]
                        for q in quotes
                    ]
                    print(f"Quotes with receipts ({len(quotes)}):")
                    print(tabulate(data, headers=headers, tablefmt="grid"))

            else:
                print("Usage: buylog receipt [attach|open|detach|list]")

        elif args.command == "scrape":
            from .services import (
                ScraperService,
                NotFoundError,
                ValidationError,
                ServiceError,
            )

            if args.scrape_command == "url":
                try:
                    result = ScraperService.scrape_price(args.url)
                    print(f"Scraped data from: {args.url}")
                    if result.get("title"):
                        print(f"  Title: {result['title'][:80]}...")
                    if result.get("price"):
                        print(f"  Price: {result['currency']} {result['price']:.2f}")
                        print(f"  Raw: {result['raw_price']}")
                    else:
                        print("  Could not extract price from page")
                except (ValidationError, ServiceError) as e:
                    print(f"Error: {e}")

            elif args.scrape_command == "quote":
                try:
                    quote = ScraperService.create_quote_from_scrape(
                        session,
                        args.url,
                        args.vendor,
                        args.product,
                        getattr(args, "brand", None),
                    )
                    print(f"Created quote #{quote.id} from scraped URL:")
                    print(f"  Product: {quote.product.name}")
                    print(f"  Vendor: {quote.vendor.name}")
                    print(f"  Price: ${quote.value:.2f}")
                except (NotFoundError, ValidationError, ServiceError) as e:
                    print(f"Error: {e}")

            else:
                print("Usage: buylog scrape [url|quote]")

        elif args.command == "report":
            from .services import ReportService, ValidationError

            output_file = getattr(args, "output", None)

            if args.report_command == "price-comparison":
                try:
                    filter_term = getattr(args, "filter", None)
                    result = ReportService.generate_report(
                        session,
                        "price-comparison",
                        output_file,
                        filter_term=filter_term,
                    )
                    if output_file:
                        print(f"Generated price comparison report: {result}")
                    else:
                        print(result)
                except ValidationError as e:
                    print(f"Error: {e}")

            elif args.report_command == "purchase-summary":
                try:
                    result = ReportService.generate_report(
                        session,
                        "purchase-summary",
                        output_file,
                    )
                    if output_file:
                        print(f"Generated purchase summary report: {result}")
                    else:
                        print(result)
                except ValidationError as e:
                    print(f"Error: {e}")

            elif args.report_command == "vendor-analysis":
                try:
                    result = ReportService.generate_report(
                        session,
                        "vendor-analysis",
                        output_file,
                    )
                    if output_file:
                        print(f"Generated vendor analysis report: {result}")
                    else:
                        print(result)
                except ValidationError as e:
                    print(f"Error: {e}")

            else:
                print("Usage: buylog report [price-comparison|purchase-summary|vendor-analysis]")

    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error: {e}")
        if "UNIQUE constraint failed" in str(e):
            print("Error: Duplicate entry. Please use a unique name.")
        else:
            print(f"Error: Database constraint violation: {e}")
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error: {e}")
        print(f"Error: Database error occurred: {e}")
    except ValueError as e:
        session.rollback()
        logger.warning(f"Invalid input: {e}")
        print(f"Error: Invalid input - {e}")
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        print("\nOperation cancelled by user.")
        session.rollback()
    except Exception as e:
        session.rollback()
        logger.exception(f"Unexpected error: {e}")
        print(f"Error: Unexpected error occurred: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
