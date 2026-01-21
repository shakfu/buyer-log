# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-01-21

### Added
- **Quote Analysis Features** - Tools for making better purchasing decisions
  - **Best Price Detection** - Automatically identifies lowest price per product
  - **Total Cost Calculation** - Includes discount, shipping, and tax in price comparison
  - **Price History Tracking** - Records all price changes with timestamps
  - **Price Trend Indicators** - Shows if prices are going up (^), down (v), stable (-), or new (*)
  - **Price Alerts** - Set threshold alerts and get notified when prices drop

- **New Models**
  - `QuoteHistory` - Tracks price changes (create/update events) for quotes
  - `PriceAlert` - Price threshold alerts with product association and trigger tracking

- **New Services**
  - `QuoteHistoryService` - Record changes, get history, compute trends
  - `PriceAlertService` - Create, check, trigger, and manage price alerts
  - Extended `QuoteService` with `get_best_prices_by_product()` and `update_price()`

- **CLI Commands**
  - `buyer alert add <product> <threshold>` - Create price alert
  - `buyer alert list [--triggered]` - List all or triggered alerts
  - `buyer alert deactivate <id>` - Deactivate an alert
  - `buyer history --product <name>` - View product price history
  - `buyer history --quote-id <id>` - View quote price history
  - Extended `buyer add` with `--shipping` and `--tax-rate` options

- **TUI Enhancements**
  - New **Alerts tab** for managing price alerts
  - Best prices highlighted in **green** in Quotes tab
  - **Total cost** column showing calculated total with shipping/tax
  - **Trend indicator** column (^/v/-/*)
  - Products with triggered alerts highlighted in **yellow**

- **Quote Model Extensions**
  - `shipping_cost` field for shipping charges
  - `tax_rate` field for tax percentage
  - `created_at` timestamp
  - `total_cost` property calculating `(base * (1-discount) + shipping) * (1 + tax_rate)`

- **Tests**
  - `test_quote_analysis.py` with 30 new tests covering all quote analysis features

## [0.2.0] - 2026-01-21

### Added
- **Textual TUI** - Interactive terminal user interface (`buyer tui`)
  - Tabbed interface for Brands, Products, Vendors, Quotes, and Forex
  - DataTables with row selection and keyboard navigation
  - Modal forms for adding new entities
  - Delete confirmation dialogs
  - Search/filter functionality across all tables
  - Keyboard shortcuts (q=quit, a=add, d=delete, r=refresh, s=search)
- **Database seeding** - `buyer seed` command to populate sample data
  - 10 sample brands (Apple, Samsung, Sony, etc.)
  - 14 sample products
  - 9 sample vendors with various currencies
  - 5 forex rates (EUR, GBP, JPY, CAD, AUD)
  - 21 sample quotes with currency conversion

### Changed
- Default log level changed from DEBUG to INFO (reduces SQLAlchemy noise)

### Removed
- **Web interface** - Removed FastAPI/HTMX web UI (`web.py`)
- **Pydantic schemas** - Removed `schemas.py` (was only used by web interface)
- **Dependencies** - Removed `fastapi`, `jinja2`, `pydantic` from requirements

## [0.1.0] - Initial Release

### Added
- Command Line Interface with CRUD operations
- SQLAlchemy ORM models (Brand, Product, Vendor, Quote, Forex)
- Service layer with business logic separation
- Multi-currency support with forex conversion
- Audit logging for entity changes
- pytest test suite with Factory Boy
