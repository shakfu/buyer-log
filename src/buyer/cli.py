#!/usr/bin/env python3
"""CLI interface for buyer tool with CRUD operations"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker, Session as SessionType
from tabulate import tabulate
from .models import Base, Brand, Product, Vendor, Quote, Forex, QuoteHistory, PriceAlert
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


def add_quote(session, vendor_name, product_name, price, brand_name=None, shipping_cost=None, tax_rate=None):
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
            print(f"Error: Invalid date format. Use YYYY-MM-DD")
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
        results = BrandService.get_all(session, filter_by=filter_by, limit=limit)
        headers = ["ID", "Name", "Products"]
        data = [
            [b.id, b.name, ", ".join([p.name for p in b.products])] for b in results
        ]
        print(tabulate(data, headers=headers, tablefmt="grid"))

    elif entity_type == "products":
        results = ProductService.get_all(session, filter_by=filter_by, limit=limit)
        headers = ["ID", "Name", "Brand"]
        data = [[p.id, p.name, p.brand.name] for p in results]
        print(tabulate(data, headers=headers, tablefmt="grid"))

    elif entity_type == "vendors":
        results = VendorService.get_all(session, filter_by=filter_by, limit=limit)
        headers = ["ID", "Name", "Currency", "Quotes"]
        data = [[v.id, v.name, v.currency, len(v.quotes)] for v in results]
        print(tabulate(data, headers=headers, tablefmt="grid"))

    elif entity_type == "quotes":
        results = QuoteService.get_all(session, filter_by=filter_by, limit=limit)
        headers = ["ID", "Vendor", "Product", "Price", "Currency"]
        data = [
            [
                q.id,
                q.vendor.name,
                f"{q.product.brand.name} {q.product.name}",
                q.value,
                q.currency,
            ]
            for q in results
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
        "Apple", "Samsung", "Sony", "LG", "Dell",
        "HP", "Lenovo", "Asus", "Acer", "Microsoft"
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

    # Products
    products_data = [
        ("Apple", "iPhone 15 Pro"),
        ("Apple", "MacBook Air M3"),
        ("Apple", "iPad Pro 12.9"),
        ("Samsung", "Galaxy S24 Ultra"),
        ("Samsung", "Galaxy Tab S9"),
        ("Sony", "WH-1000XM5"),
        ("Sony", "PlayStation 5"),
        ("LG", "C3 OLED 65"),
        ("Dell", "XPS 15"),
        ("HP", "Spectre x360"),
        ("Lenovo", "ThinkPad X1 Carbon"),
        ("Asus", "ROG Zephyrus G14"),
        ("Microsoft", "Surface Pro 9"),
        ("Microsoft", "Xbox Series X"),
    ]
    products = {}
    for brand_name, product_name in products_data:
        existing = Product.by_name(session, product_name)
        if existing:
            products[product_name] = existing
        else:
            product = Product(name=product_name, brand=brands[brand_name])
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
                discount=discount
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
    opt("--usd-per-unit", type=float, required=True, help="USD per unit (e.g., 1.085 for EUR)")
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
    alert_subparsers = alert_parser.add_subparsers(dest="alert_command", help="Alert commands")

    # Alert add
    alert_add_parser = alert_subparsers.add_parser("add", help="Add a price alert")
    alert_add_parser.add_argument("product", type=str, help="Product name")
    alert_add_parser.add_argument("threshold", type=float, help="Price threshold")

    # Alert list
    alert_list_parser = alert_subparsers.add_parser("list", help="List price alerts")
    alert_list_parser.add_argument("--triggered", action="store_true", help="Show only triggered alerts")

    # Alert deactivate
    alert_deactivate_parser = alert_subparsers.add_parser("deactivate", help="Deactivate an alert")
    alert_deactivate_parser.add_argument("id", type=int, help="Alert ID")

    # History command
    history_parser = subparsers.add_parser("history", help="View price history")
    history_parser.add_argument("--product", type=str, help="Product name")
    history_parser.add_argument("--quote-id", type=int, help="Quote ID")

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
                    getattr(args, 'shipping', None),
                    getattr(args, 'tax_rate', None),
                )

            else:
                print("Invalid combination of arguments for 'add' command")
                add_parser.print_help()

        elif args.command == "add-fx":
            add_fx(session, args.code, args.usd_per_unit, args.date if hasattr(args, 'date') else None)

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
                    alert = PriceAlertService.create(session, args.product, args.threshold)
                    print(f"Created alert #{alert.id} for '{args.product}' at ${args.threshold:.2f}")
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
                        [a.id, a.product.name, f"${a.threshold_value:.2f}", str(a.triggered_at)]
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
                print("Usage: buyer alert [add|list|deactivate]")

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
                print("Usage: buyer history [--product NAME | --quote-id ID]")

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
