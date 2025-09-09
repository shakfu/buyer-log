#!/usr/bin/env python3
"""FastAPI web interface for buyer tool"""

from typing import Optional, List
from pathlib import Path
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from fastapi import FastAPI, HTTPException, Depends, Form
from fastapi.responses import HTMLResponse
from .models import Base, Brand, Product, Vendor, Quote

# Database setup
DB_PATH = Path.home() / '.buyer' / 'buyer.db'
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(f'sqlite:///{DB_PATH}')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

app = FastAPI(title="Buyer", description="Purchasing support and vendor quote management")


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
        .entity-item { padding: 10px; margin: 5px 0; background: #f8f9fa; border-radius: 3px; }
        .error { color: red; margin: 10px 0; }
        .success { color: green; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Buyer - Purchasing Management</h1>
        
        <div class="section">
            <h2>Add Brand</h2>
            <form method="post" action="/brands">
                <div class="form-group">
                    <label>Brand Name:</label>
                    <input type="text" name="name" required>
                </div>
                <button type="submit">Add Brand</button>
            </form>
        </div>
        
        <div class="section">
            <h2>Add Product</h2>
            <form method="post" action="/products">
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
        </div>
        
        <div class="section">
            <h2>Add Vendor</h2>
            <form method="post" action="/vendors">
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
        </div>
        
        <div class="section">
            <h2>Add Quote</h2>
            <form method="post" action="/quotes">
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
        </div>
        
        <div class="section">
            <h2>View Data</h2>
            <p>
                <a href="/brands/list">View Brands</a> | 
                <a href="/products/list">View Products</a> | 
                <a href="/vendors/list">View Vendors</a> | 
                <a href="/quotes/list">View Quotes</a>
            </p>
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


@app.post("/brands")
async def add_brand(
    name: str = Form(...),
    session = Depends(get_session)
):
    """Add a new brand"""
    existing = Brand.by_name(session, name)
    if existing:
        raise HTTPException(status_code=400, detail=f"Brand '{name}' already exists")
    
    brand = Brand(name=name)
    session.add(brand)
    session.commit()
    return {"message": f"Added brand: {name}", "id": brand.id}


@app.post("/products")
async def add_product(
    name: str = Form(...),
    brand_name: str = Form(...),
    session = Depends(get_session)
):
    """Add a new product under a brand"""
    brand = Brand.by_name(session, brand_name)
    if not brand:
        brand = Brand(name=brand_name)
        session.add(brand)
        session.flush()
    
    existing = Product.by_name(session, name)
    if existing:
        raise HTTPException(status_code=400, detail=f"Product '{name}' already exists")
    
    product = Product(name=name, brand=brand)
    session.add(product)
    session.commit()
    return {"message": f"Added product: {name} under brand: {brand_name}", "id": product.id}


@app.post("/vendors")
async def add_vendor(
    name: str = Form(...),
    currency: str = Form("USD"),
    discount_code: Optional[str] = Form(None),
    discount: float = Form(0.0),
    session = Depends(get_session)
):
    """Add a new vendor"""
    existing = Vendor.by_name(session, name)
    if existing:
        raise HTTPException(status_code=400, detail=f"Vendor '{name}' already exists")
    
    vendor = Vendor(
        name=name,
        currency=currency,
        discount_code=discount_code or None,
        discount=discount
    )
    session.add(vendor)
    session.commit()
    return {"message": f"Added vendor: {name} (currency: {currency})", "id": vendor.id}


@app.post("/quotes")
async def add_quote(
    vendor_name: str = Form(...),
    product_name: str = Form(...),
    value: float = Form(...),
    session = Depends(get_session)
):
    """Add a quote from a vendor for a product"""
    vendor = Vendor.by_name(session, vendor_name)
    if not vendor:
        raise HTTPException(status_code=404, detail=f"Vendor '{vendor_name}' not found")
    
    product = Product.by_name(session, product_name)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_name}' not found")
    
    quote = Quote(
        vendor=vendor,
        product=product,
        currency=vendor.currency,
        value=value
    )
    session.add(quote)
    session.commit()
    return {"message": f"Added quote: {vendor_name} -> {product_name} = {value} {vendor.currency}", "id": quote.id}


@app.get("/brands")
async def get_brands(session = Depends(get_session)):
    """Get all brands"""
    brands = session.execute(select(Brand)).scalars().all()
    return [{"id": b.id, "name": b.name, "product_count": len(b.products)} for b in brands]


@app.get("/brands/list", response_class=HTMLResponse)
async def list_brands_html(session = Depends(get_session)):
    """List brands in HTML format"""
    brands = session.execute(select(Brand)).scalars().all()
    content = ""
    for brand in brands:
        products = [p.name for p in brand.products]
        products_str = ', '.join(products) if products else 'none'
        content += f'<div class="entity-item">Brand: {brand.name} (products: {products_str})</div>'
    
    return LIST_TEMPLATE.format(title="Brands", content=content)


@app.get("/products")
async def get_products(session = Depends(get_session)):
    """Get all products"""
    products = session.execute(select(Product)).scalars().all()
    return [{"id": p.id, "name": p.name, "brand": p.brand.name} for p in products]


@app.get("/products/list", response_class=HTMLResponse)
async def list_products_html(session = Depends(get_session)):
    """List products in HTML format"""
    products = session.execute(select(Product)).scalars().all()
    content = ""
    for product in products:
        content += f'<div class="entity-item">Product: {product.name} (brand: {product.brand.name})</div>'
    
    return LIST_TEMPLATE.format(title="Products", content=content)


@app.get("/vendors")
async def get_vendors(session = Depends(get_session)):
    """Get all vendors"""
    vendors = session.execute(select(Vendor)).scalars().all()
    return [{"id": v.id, "name": v.name, "currency": v.currency, "quote_count": len(v.quotes)} for v in vendors]


@app.get("/vendors/list", response_class=HTMLResponse)
async def list_vendors_html(session = Depends(get_session)):
    """List vendors in HTML format"""
    vendors = session.execute(select(Vendor)).scalars().all()
    content = ""
    for vendor in vendors:
        quote_count = len(vendor.quotes)
        content += f'<div class="entity-item">Vendor: {vendor.name} (currency: {vendor.currency}, quotes: {quote_count})</div>'
    
    return LIST_TEMPLATE.format(title="Vendors", content=content)


@app.get("/quotes")
async def get_quotes(session = Depends(get_session)):
    """Get all quotes"""
    quotes = session.execute(select(Quote)).scalars().all()
    return [{
        "id": q.id,
        "vendor": q.vendor.name,
        "product": q.product.name,
        "brand": q.product.brand.name,
        "value": q.value,
        "currency": q.currency
    } for q in quotes]


@app.get("/quotes/list", response_class=HTMLResponse)
async def list_quotes_html(session = Depends(get_session)):
    """List quotes in HTML format"""
    quotes = session.execute(select(Quote)).scalars().all()
    content = ""
    for quote in quotes:
        content += f'<div class="entity-item">Quote: {quote.vendor.name} → {quote.product.brand.name} {quote.product.name} = {quote.value} {quote.currency}</div>'
    
    return LIST_TEMPLATE.format(title="Quotes", content=content)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)