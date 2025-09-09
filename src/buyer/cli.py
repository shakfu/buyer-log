#!/usr/bin/env python3
"""CLI interface for buyer tool with CRUD operations"""

import argparse
import sys
from pathlib import Path
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from .models import Base, Brand, Product, Vendor, Quote

# Database setup
DB_PATH = Path.home() / '.buyer' / 'buyer.db'
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(f'sqlite:///{DB_PATH}')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


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


def add_vendor(session, name, currency='USD', discount_code=None, discount=0.0):
    """Add a new vendor"""
    existing = Vendor.by_name(session, name)
    if existing:
        print(f"Vendor '{name}' already exists")
        return existing
    
    vendor = Vendor(
        name=name, 
        currency=currency,
        discount_code=discount_code,
        discount=discount
    )
    session.add(vendor)
    session.commit()
    print(f"Added vendor: {name} (currency: {currency})")
    return vendor


def add_quote(session, vendor_name, product_name, price):
    """Add a quote from a vendor for a product"""
    vendor = Vendor.by_name(session, vendor_name)
    if not vendor:
        print(f"Vendor '{vendor_name}' not found")
        return None
    
    product = Product.by_name(session, product_name)
    if not product:
        print(f"Product '{product_name}' not found")
        return None
    
    quote = Quote(
        vendor=vendor,
        product=product,
        currency=vendor.currency,
        value=float(price)
    )
    session.add(quote)
    session.commit()
    print(f"Added quote: {vendor_name} -> {product_name} = {price} {vendor.currency}")
    return quote


def list_entities(session, entity_type):
    """List all entities of a given type"""
    if entity_type == 'brands':
        brands = session.execute(select(Brand)).scalars().all()
        for brand in brands:
            products = [p.name for p in brand.products]
            print(f"Brand: {brand.name} (products: {', '.join(products) if products else 'none'})")
    
    elif entity_type == 'products':
        products = session.execute(select(Product)).scalars().all()
        for product in products:
            print(f"Product: {product.name} (brand: {product.brand.name})")
    
    elif entity_type == 'vendors':
        vendors = session.execute(select(Vendor)).scalars().all()
        for vendor in vendors:
            quote_count = len(vendor.quotes)
            print(f"Vendor: {vendor.name} (currency: {vendor.currency}, quotes: {quote_count})")
    
    elif entity_type == 'quotes':
        quotes = session.execute(select(Quote)).scalars().all()
        for quote in quotes:
            print(f"Quote: {quote.vendor.name} -> {quote.product.brand.name} {quote.product.name} = {quote.value} {quote.currency}")


def main():
    parser = argparse.ArgumentParser(description='Buyer - Purchasing support and vendor quote management')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add entities')
    opt = add_parser.add_argument
    opt('-b', '--brand', type=str, help='Add a brand')
    opt('-p', '--product', type=str, help='Add a product (requires --brand)')
    opt('-v', '--vendor', type=str, help='Add a vendor')
    opt('-q', '--quote', type=float, help='Add a quote (requires --vendor and --product)')
    opt('-c', '--currency', type=str, default='USD', help='Currency for vendor (default: USD)')
    opt('-dc', '--discount-code', type=str, help='Discount code for vendor')
    opt('-d', '--discount', type=float, default=0.0, help='Discount percentage for vendor')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List entities')
    list_parser.add_argument('type', choices=['brands', 'products', 'vendors', 'quotes'], 
                           help='Type of entity to list')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    session = Session()
    
    try:
        if args.command == 'add':
            if args.brand and not args.product and not args.vendor:
                # Add brand only
                add_brand(session, args.brand)
            
            elif args.brand and args.product and not args.vendor:
                # Add product under brand
                add_product(session, args.brand, args.product)
            
            elif args.vendor and not args.product:
                # Add vendor only
                add_vendor(session, args.vendor, args.currency, args.discount_code, args.discount)
            
            elif args.vendor and args.product and args.quote is not None:
                # Add quote
                add_quote(session, args.vendor, args.product, args.quote)
            
            else:
                print("Invalid combination of arguments for 'add' command")
                add_parser.print_help()
        
        elif args.command == 'list':
            list_entities(session, args.type)
        
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()


if __name__ == '__main__':
    main()