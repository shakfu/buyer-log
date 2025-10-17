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
from .models import Base, Brand, Product, Vendor, Quote, Forex
from .config import Config

# Setup logging
logger = Config.setup_logging()

# Database setup
engine = Config.get_engine()
Base.metadata.create_all(engine)
Session = Config.get_session_maker()


def add_brand(session, name):
    """Add a new brand"""
    existing = Brand.by_name(session, name)
    if existing:
        print(f"Brand '{name}' already exists")
        return existing

    brand = Brand(name=name)
    session.add(brand)
    session.commit()
    print(f"Added brand: {name}")
    return brand


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


def add_quote(session, vendor_name, product_name, price, brand_name=None):
    """Add a quote from a vendor for a product"""
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
    )
    session.add(quote)
    session.commit()
    print(f"Added quote: {vendor_name} -> {product_name} = {price} {vendor.currency}")
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


def list_entities(session, entity_type, filter_by=None, sort_by=None):
    """List all entities of a given type"""
    if entity_type == "brands":
        query = select(Brand)
        if filter_by:
            query = query.where(Brand.name.ilike(f"%{filter_by}%"))
        if sort_by:
            query = query.order_by(sort_by)
        results = session.execute(query).scalars().all()
        headers = ["ID", "Name", "Products"]
        data = [
            [b.id, b.name, ", ".join([p.name for p in b.products])] for b in results
        ]
        print(tabulate(data, headers=headers, tablefmt="grid"))

    elif entity_type == "products":
        query = select(Product)
        if filter_by:
            query = query.where(Product.name.ilike(f"%{filter_by}%"))
        if sort_by:
            query = query.order_by(sort_by)
        results = session.execute(query).scalars().all()
        headers = ["ID", "Name", "Brand"]
        data = [[p.id, p.name, p.brand.name] for p in results]
        print(tabulate(data, headers=headers, tablefmt="grid"))

    elif entity_type == "vendors":
        query = select(Vendor)
        if filter_by:
            query = query.where(Vendor.name.ilike(f"%{filter_by}%"))
        if sort_by:
            query = query.order_by(sort_by)
        results = session.execute(query).scalars().all()
        headers = ["ID", "Name", "Currency", "Quotes"]
        data = [[v.id, v.name, v.currency, len(v.quotes)] for v in results]
        print(tabulate(data, headers=headers, tablefmt="grid"))

    elif entity_type == "quotes":
        query = select(Quote)
        if filter_by:
            query = query.join(Product).where(Product.name.ilike(f"%{filter_by}%"))
        if sort_by:
            query = query.order_by(sort_by)
        results = session.execute(query).scalars().all()
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
                add_quote(session, args.vendor, args.product, args.quote, args.brand)

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
