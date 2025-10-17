#!/usr/bin/env python3
"""FastAPI web interface for buyer tool"""

from typing import Optional, List
from pathlib import Path
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from fastapi import FastAPI, HTTPException, Depends, Form
from fastapi.responses import HTMLResponse
from .models import Base, Brand, Product, Vendor, Quote
from .config import Config

# Database setup
engine = Config.get_engine()
Base.metadata.create_all(engine)
Session = Config.get_session_maker()

app = FastAPI(
    title="Buyer", description="Purchasing support and vendor quote management"
)


def get_session():
    """Dependency to get database session"""
    session = Session()
    try:
        yield session
    finally:
        session.close()


# HTML templates (embedded for simplicity)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Buyer - Purchasing Management</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, select { padding: 8px; width: 300px; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
        button:hover { background: #0056b3; }
        .section { margin: 30px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
        .entity-list { margin-top: 20px; }
        .entity-item { padding: 10px; margin: 5px 0; background: #f8f9fa; border-radius: 3px; display: flex; justify-content: space-between; align-items: center; }
        .error { color: red; margin: 10px 0; padding: 10px; background: #ffe6e6; border-radius: 3px; }
        .success { color: green; margin: 10px 0; padding: 10px; background: #e6ffe6; border-radius: 3px; }
        .delete-btn { padding: 5px 10px; background: #dc3545; color: white; border: none; cursor: pointer; border-radius: 3px; font-size: 12px; }
        .delete-btn:hover { background: #c82333; }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/htmx.org@2.0.7/dist/htmx.min.js" integrity="sha384-ZBXiYtYQ6hJ2Y0ZNoYuI+Nq5MqWBr+chMrS/RkXpNzQCApHEhOt2aY8EJgqwHLkJ" crossorigin="anonymous"></script>
</head>
<body>
    <div class="container">
        <h1>Buyer - Purchasing Management</h1>
        
        <div class="section">
            <h2>Add Brand</h2>
            <form hx-post="/brands" hx-target="#brand-response" hx-swap="innerHTML" hx-on::after-request="this.reset()">
                <div class="form-group">
                    <label>Brand Name:</label>
                    <input type="text" name="name" required>
                </div>
                <button type="submit">Add Brand</button>
            </form>
            <div id="brand-response"></div>
            <div class="entity-list">
                <h3>Current Brands</h3>
                <div id="brands-list" hx-get="/brands/fragment" hx-trigger="load"></div>
            </div>
        </div>
        
        <div class="section">
            <h2>Add Product</h2>
            <form hx-post="/products" hx-target="#product-response" hx-swap="innerHTML" hx-on::after-request="this.reset()">
                <div class="form-group">
                    <label>Brand Name:</label>
                    <input type="text" name="brand_name" required>
                </div>
                <div class="form-group">
                    <label>Product Name:</label>
                    <input type="text" name="name" required>
                </div>
                <button type="submit">Add Product</button>
            </form>
            <div id="product-response"></div>
            <div class="entity-list">
                <h3>Current Products</h3>
                <div id="products-list" hx-get="/products/fragment" hx-trigger="load"></div>
            </div>
        </div>
        
        <div class="section">
            <h2>Add Vendor</h2>
            <form hx-post="/vendors" hx-target="#vendor-response" hx-swap="innerHTML" hx-on::after-request="this.reset()">
                <div class="form-group">
                    <label>Vendor Name:</label>
                    <input type="text" name="name" required>
                </div>
                <div class="form-group">
                    <label>Currency:</label>
                    <input type="text" name="currency" value="USD">
                </div>
                <div class="form-group">
                    <label>Discount Code (optional):</label>
                    <input type="text" name="discount_code">
                </div>
                <div class="form-group">
                    <label>Discount %:</label>
                    <input type="number" name="discount" value="0.0" step="0.01">
                </div>
                <button type="submit">Add Vendor</button>
            </form>
            <div id="vendor-response"></div>
            <div class="entity-list">
                <h3>Current Vendors</h3>
                <div id="vendors-list" hx-get="/vendors/fragment" hx-trigger="load"></div>
            </div>
        </div>
        
        <div class="section">
            <h2>Add Quote</h2>
            <form hx-post="/quotes" hx-target="#quote-response" hx-swap="innerHTML" hx-on::after-request="this.reset()">
                <div class="form-group">
                    <label>Vendor Name:</label>
                    <input type="text" name="vendor_name" required>
                </div>
                <div class="form-group">
                    <label>Product Name:</label>
                    <input type="text" name="product_name" required>
                </div>
                <div class="form-group">
                    <label>Price:</label>
                    <input type="number" name="value" step="0.01" required>
                </div>
                <button type="submit">Add Quote</button>
            </form>
            <div id="quote-response"></div>
            <div class="entity-list">
                <h3>Current Quotes</h3>
                <div id="quotes-list" hx-get="/quotes/fragment" hx-trigger="load"></div>
            </div>
        </div>
    </div>
</body>
</html>
"""

LIST_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Buyer - {title}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        .entity-item { padding: 10px; margin: 5px 0; background: #f8f9fa; border-radius: 3px; }
        a { text-decoration: none; color: #007bff; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <p><a href="/">← Back to main page</a></p>
        <div class="entity-list">
            {content}
        </div>
    </div>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def home():
    """Main page with forms"""
    return HTML_TEMPLATE


@app.post("/brands", response_class=HTMLResponse)
async def add_brand(name: str = Form(...), session=Depends(get_session)):
    """Add a new brand"""
    try:
        # Validate input
        name = name.strip()
        if not name:
            return '<div class="error">Brand name cannot be empty</div>'
        if len(name) > 255:
            return '<div class="error">Brand name too long (max 255 characters)</div>'

        existing = Brand.by_name(session, name)
        if existing:
            return f'<div class="error">Brand \'{name}\' already exists</div>'

        brand = Brand(name=name)
        session.add(brand)
        session.commit()

        # Return success message and updated brand list
        brands = session.execute(select(Brand)).scalars().all()
        items_html = ""
        for b in brands:
            products = [p.name for p in b.products]
            products_str = ", ".join(products) if products else "none"
            items_html += f"""<div class="entity-item">
                Brand: {b.name} (products: {products_str})
                <button class="delete-btn" hx-delete="/brands/{b.id}" hx-target="#brand-response" hx-confirm="Delete brand '{b.name}'?">Delete</button>
            </div>"""

        return f"""
            <div class="success">Added brand: {name}</div>
            <div id="brands-list" hx-swap-oob="true">{items_html}</div>
        """
    except IntegrityError:
        session.rollback()
        return f'<div class="error">Brand \'{name}\' already exists</div>'
    except SQLAlchemyError as e:
        session.rollback()
        return '<div class="error">Database error occurred</div>'
    except Exception as e:
        session.rollback()
        return '<div class="error">An unexpected error occurred</div>'


@app.post("/products", response_class=HTMLResponse)
async def add_product(
    name: str = Form(...), brand_name: str = Form(...), session=Depends(get_session)
):
    """Add a new product under a brand"""
    brand = Brand.by_name(session, brand_name)
    if not brand:
        brand = Brand(name=brand_name)
        session.add(brand)
        session.flush()

    existing = Product.by_name(session, name)
    if existing:
        return f"<div class=\"error\">Product '{name}' already exists</div>"

    product = Product(name=name, brand=brand)
    session.add(product)
    session.commit()

    # Return success message and updated product list
    products = session.execute(select(Product)).scalars().all()
    items_html = ""
    for p in products:
        items_html += f"""<div class="entity-item">
            Product: {p.name} (brand: {p.brand.name})
            <button class="delete-btn" hx-delete="/products/{p.id}" hx-target="#product-response" hx-confirm="Delete product '{p.name}'?">Delete</button>
        </div>"""

    return f"""
        <div class="success">Added product: {name} under brand: {brand_name}</div>
        <div id="products-list" hx-swap-oob="true">{items_html}</div>
    """


@app.post("/vendors", response_class=HTMLResponse)
async def add_vendor(
    name: str = Form(...),
    currency: str = Form("USD"),
    discount_code: Optional[str] = Form(None),
    discount: float = Form(0.0),
    session=Depends(get_session),
):
    """Add a new vendor"""
    existing = Vendor.by_name(session, name)
    if existing:
        return f"<div class=\"error\">Vendor '{name}' already exists</div>"

    vendor = Vendor(
        name=name,
        currency=currency,
        discount_code=discount_code or None,
        discount=discount,
    )
    session.add(vendor)
    session.commit()

    # Return success message and updated vendor list
    vendors = session.execute(select(Vendor)).scalars().all()
    items_html = ""
    for v in vendors:
        quote_count = len(v.quotes)
        items_html += f"""<div class="entity-item">
            Vendor: {v.name} (currency: {v.currency}, quotes: {quote_count})
            <button class="delete-btn" hx-delete="/vendors/{v.id}" hx-target="#vendor-response" hx-confirm="Delete vendor '{v.name}'?">Delete</button>
        </div>"""

    return f"""
        <div class="success">Added vendor: {name} (currency: {currency})</div>
        <div id="vendors-list" hx-swap-oob="true">{items_html}</div>
    """


@app.post("/quotes", response_class=HTMLResponse)
async def add_quote(
    vendor_name: str = Form(...),
    product_name: str = Form(...),
    value: float = Form(...),
    session=Depends(get_session),
):
    """Add a quote from a vendor for a product"""
    vendor = Vendor.by_name(session, vendor_name)
    if not vendor:
        return f"<div class=\"error\">Vendor '{vendor_name}' not found</div>"

    product = Product.by_name(session, product_name)
    if not product:
        return f"<div class=\"error\">Product '{product_name}' not found</div>"

    quote = Quote(vendor=vendor, product=product, currency=vendor.currency, value=value)
    session.add(quote)
    session.commit()

    # Return success message and updated quote list
    quotes = session.execute(select(Quote)).scalars().all()
    items_html = ""
    for q in quotes:
        items_html += f"""<div class="entity-item">
            Quote: {q.vendor.name} → {q.product.brand.name} {q.product.name} = {q.value} {q.currency}
            <button class="delete-btn" hx-delete="/quotes/{q.id}" hx-target="#quote-response" hx-confirm="Delete quote?">Delete</button>
        </div>"""

    return f"""
        <div class="success">Added quote: {vendor_name} → {product_name} = {value} {vendor.currency}</div>
        <div id="quotes-list" hx-swap-oob="true">{items_html}</div>
    """


@app.delete("/brands/{brand_id}", response_class=HTMLResponse)
async def delete_brand(brand_id: int, session=Depends(get_session)):
    """Delete a brand"""
    brand = session.get(Brand, brand_id)
    if not brand:
        return '<div class="error">Brand not found</div>'

    name = brand.name
    session.delete(brand)
    session.commit()

    # Return updated list and success message
    brands = session.execute(select(Brand)).scalars().all()
    items_html = ""
    for b in brands:
        products = [p.name for p in b.products]
        products_str = ", ".join(products) if products else "none"
        items_html += f"""<div class="entity-item">
            Brand: {b.name} (products: {products_str})
            <button class="delete-btn" hx-delete="/brands/{b.id}" hx-target="#brand-response" hx-confirm="Delete brand '{b.name}'?">Delete</button>
        </div>"""

    return f"""
        <div class="success">Deleted brand: {name}</div>
        <div id="brands-list" hx-swap-oob="true">{items_html}</div>
    """


@app.get("/brands/fragment", response_class=HTMLResponse)
async def get_brands_fragment(session=Depends(get_session)):
    """Get brands list fragment"""
    brands = session.execute(select(Brand)).scalars().all()
    items_html = ""
    for b in brands:
        products = [p.name for p in b.products]
        products_str = ", ".join(products) if products else "none"
        items_html += f"""<div class="entity-item">
            Brand: {b.name} (products: {products_str})
            <button class="delete-btn" hx-delete="/brands/{b.id}" hx-target="#brand-response" hx-confirm="Delete brand '{b.name}'?">Delete</button>
        </div>"""
    return items_html


@app.get("/brands")
async def get_brands(session=Depends(get_session)):
    """Get all brands"""
    brands = session.execute(select(Brand)).scalars().all()
    return [
        {"id": b.id, "name": b.name, "product_count": len(b.products)} for b in brands
    ]


@app.get("/brands/list", response_class=HTMLResponse)
async def list_brands_html(session=Depends(get_session)):
    """List brands in HTML format"""
    brands = session.execute(select(Brand)).scalars().all()
    content = ""
    for brand in brands:
        products = [p.name for p in brand.products]
        products_str = ", ".join(products) if products else "none"
        content += f'<div class="entity-item">Brand: {brand.name} (products: {products_str})</div>'

    return LIST_TEMPLATE.format(title="Brands", content=content)


@app.delete("/products/{product_id}", response_class=HTMLResponse)
async def delete_product(product_id: int, session=Depends(get_session)):
    """Delete a product"""
    product = session.get(Product, product_id)
    if not product:
        return '<div class="error">Product not found</div>'

    name = product.name
    session.delete(product)
    session.commit()

    # Return updated list and success message
    products = session.execute(select(Product)).scalars().all()
    items_html = ""
    for p in products:
        items_html += f"""<div class="entity-item">
            Product: {p.name} (brand: {p.brand.name})
            <button class="delete-btn" hx-delete="/products/{p.id}" hx-target="#product-response" hx-confirm="Delete product '{p.name}'?">Delete</button>
        </div>"""

    return f"""
        <div class="success">Deleted product: {name}</div>
        <div id="products-list" hx-swap-oob="true">{items_html}</div>
    """


@app.get("/products/fragment", response_class=HTMLResponse)
async def get_products_fragment(session=Depends(get_session)):
    """Get products list fragment"""
    products = session.execute(select(Product)).scalars().all()
    items_html = ""
    for p in products:
        items_html += f"""<div class="entity-item">
            Product: {p.name} (brand: {p.brand.name})
            <button class="delete-btn" hx-delete="/products/{p.id}" hx-target="#product-response" hx-confirm="Delete product '{p.name}'?">Delete</button>
        </div>"""
    return items_html


@app.get("/products")
async def get_products(session=Depends(get_session)):
    """Get all products"""
    products = session.execute(select(Product)).scalars().all()
    return [{"id": p.id, "name": p.name, "brand": p.brand.name} for p in products]


@app.get("/products/list", response_class=HTMLResponse)
async def list_products_html(session=Depends(get_session)):
    """List products in HTML format"""
    products = session.execute(select(Product)).scalars().all()
    content = ""
    for product in products:
        content += f'<div class="entity-item">Product: {product.name} (brand: {product.brand.name})</div>'

    return LIST_TEMPLATE.format(title="Products", content=content)


@app.delete("/vendors/{vendor_id}", response_class=HTMLResponse)
async def delete_vendor(vendor_id: int, session=Depends(get_session)):
    """Delete a vendor"""
    vendor = session.get(Vendor, vendor_id)
    if not vendor:
        return '<div class="error">Vendor not found</div>'

    name = vendor.name
    session.delete(vendor)
    session.commit()

    # Return updated list and success message
    vendors = session.execute(select(Vendor)).scalars().all()
    items_html = ""
    for v in vendors:
        quote_count = len(v.quotes)
        items_html += f"""<div class="entity-item">
            Vendor: {v.name} (currency: {v.currency}, quotes: {quote_count})
            <button class="delete-btn" hx-delete="/vendors/{v.id}" hx-target="#vendor-response" hx-confirm="Delete vendor '{v.name}'?">Delete</button>
        </div>"""

    return f"""
        <div class="success">Deleted vendor: {name}</div>
        <div id="vendors-list" hx-swap-oob="true">{items_html}</div>
    """


@app.get("/vendors/fragment", response_class=HTMLResponse)
async def get_vendors_fragment(session=Depends(get_session)):
    """Get vendors list fragment"""
    vendors = session.execute(select(Vendor)).scalars().all()
    items_html = ""
    for v in vendors:
        quote_count = len(v.quotes)
        items_html += f"""<div class="entity-item">
            Vendor: {v.name} (currency: {v.currency}, quotes: {quote_count})
            <button class="delete-btn" hx-delete="/vendors/{v.id}" hx-target="#vendor-response" hx-confirm="Delete vendor '{v.name}'?">Delete</button>
        </div>"""
    return items_html


@app.get("/vendors")
async def get_vendors(session=Depends(get_session)):
    """Get all vendors"""
    vendors = session.execute(select(Vendor)).scalars().all()
    return [
        {
            "id": v.id,
            "name": v.name,
            "currency": v.currency,
            "quote_count": len(v.quotes),
        }
        for v in vendors
    ]


@app.get("/vendors/list", response_class=HTMLResponse)
async def list_vendors_html(session=Depends(get_session)):
    """List vendors in HTML format"""
    vendors = session.execute(select(Vendor)).scalars().all()
    content = ""
    for vendor in vendors:
        quote_count = len(vendor.quotes)
        content += f'<div class="entity-item">Vendor: {vendor.name} (currency: {vendor.currency}, quotes: {quote_count})</div>'

    return LIST_TEMPLATE.format(title="Vendors", content=content)


@app.delete("/quotes/{quote_id}", response_class=HTMLResponse)
async def delete_quote(quote_id: int, session=Depends(get_session)):
    """Delete a quote"""
    quote = session.get(Quote, quote_id)
    if not quote:
        return '<div class="error">Quote not found</div>'

    desc = f"{quote.vendor.name} → {quote.product.name}"
    session.delete(quote)
    session.commit()

    # Return updated list and success message
    quotes = session.execute(select(Quote)).scalars().all()
    items_html = ""
    for q in quotes:
        items_html += f"""<div class="entity-item">
            Quote: {q.vendor.name} → {q.product.brand.name} {q.product.name} = {q.value} {q.currency}
            <button class="delete-btn" hx-delete="/quotes/{q.id}" hx-target="#quote-response" hx-confirm="Delete quote?">Delete</button>
        </div>"""

    return f"""
        <div class="success">Deleted quote: {desc}</div>
        <div id="quotes-list" hx-swap-oob="true">{items_html}</div>
    """


@app.get("/quotes/fragment", response_class=HTMLResponse)
async def get_quotes_fragment(session=Depends(get_session)):
    """Get quotes list fragment"""
    quotes = session.execute(select(Quote)).scalars().all()
    items_html = ""
    for q in quotes:
        items_html += f"""<div class="entity-item">
            Quote: {q.vendor.name} → {q.product.brand.name} {q.product.name} = {q.value} {q.currency}
            <button class="delete-btn" hx-delete="/quotes/{q.id}" hx-target="#quote-response" hx-confirm="Delete quote?">Delete</button>
        </div>"""
    return items_html


@app.get("/quotes")
async def get_quotes(session=Depends(get_session)):
    """Get all quotes"""
    quotes = session.execute(select(Quote)).scalars().all()
    return [
        {
            "id": q.id,
            "vendor": q.vendor.name,
            "product": q.product.name,
            "brand": q.product.brand.name,
            "value": q.value,
            "currency": q.currency,
        }
        for q in quotes
    ]


@app.get("/quotes/list", response_class=HTMLResponse)
async def list_quotes_html(session=Depends(get_session)):
    """List quotes in HTML format"""
    quotes = session.execute(select(Quote)).scalars().all()
    content = ""
    for quote in quotes:
        content += f'<div class="entity-item">Quote: {quote.vendor.name} → {quote.product.brand.name} {quote.product.name} = {quote.value} {quote.currency}</div>'

    return LIST_TEMPLATE.format(title="Quotes", content=content)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
