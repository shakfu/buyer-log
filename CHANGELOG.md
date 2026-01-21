# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.7]

### Added

- **Integration Features** - Connect with external tools and data

  - **Clipboard Support** - Copy data to clipboard
    - `buylog clipboard quote <id>` - Copy quote details to clipboard
    - `buylog clipboard product <name>` - Copy product info to clipboard
    - `buylog clipboard vendor <name>` - Copy vendor info (including URL) to clipboard
    - TUI: Press `y` to copy selected item to clipboard

  - **Vendor URL Management** - Store and open vendor URLs
    - `buylog vendor-url set <vendor> <url>` - Set vendor URL
    - `buylog vendor-url open <vendor>` - Open vendor URL in browser
    - `buylog vendor-url clear <vendor>` - Clear vendor URL
    - TUI: Press `o` on vendors tab to open selected vendor's URL
    - New "URL" column in vendors table showing link indicator

  - **Receipt Attachments** - Link receipt files to quotes
    - `buylog receipt attach <quote_id> <file_path>` - Attach receipt to quote
    - `buylog receipt open <quote_id>` - Open receipt file
    - `buylog receipt detach <quote_id>` - Remove receipt from quote
    - `buylog receipt list` - List all quotes with receipts

  - **Web Scraping** - Fetch product prices from URLs
    - `buylog scrape url <url>` - Scrape price from URL
    - `buylog scrape quote <url> --vendor <name> --product <name>` - Create quote from scraped URL
    - Supports JSON-LD structured data and common price patterns
    - Auto-sets vendor URL from scraped page

- **New Model Fields**
  - `Vendor.url` - Store vendor website URL
  - `Quote.receipt_path` - Store path to receipt file

- **New Services**
  - `ClipboardService` - Copy entity data to clipboard
  - `VendorURLService` - Manage vendor URLs
  - `ReceiptService` - Attach/open/detach receipt files
  - `ScraperService` - Web scraping for product prices

- **Tests** - 38 new tests for integration features (203 total tests)

## [0.1.6]

### Added
- **Data Management Features** - Import, export, backup, and deduplication

  - **CSV/JSON Import** - Bulk import quotes from files
    - `buylog import quotes data.csv` - Import from CSV
    - `buylog import quotes data.json` - Import from JSON
    - Auto-creates missing vendors, products, and brands
    - Use `--no-create` to require existing entities

  - **Export Reports** - Export data to CSV or Markdown
    - `buylog export quotes --format csv --file quotes.csv`
    - `buylog export quotes --format markdown --file report.md`
    - `buylog export products --file products.csv`
    - `buylog export vendors --file vendors.csv`
    - Supports `--filter` for filtered exports

  - **Backup/Restore** - Database backup management
    - `buylog backup` - Create timestamped backup
    - `buylog backup --output my-backup.db` - Custom backup path
    - `buylog restore my-backup.db` - Restore from backup
    - `buylog backups` - List available backups

  - **Merge Duplicates** - Detect and merge similar entities
    - `buylog duplicates vendors` - Find similar vendors
    - `buylog duplicates products` - Find similar products
    - `buylog duplicates merge-vendors 1 2 3` - Merge vendors 2,3 into 1
    - `buylog duplicates merge-products 1 2 3` - Merge products 2,3 into 1
    - Uses Jaccard similarity with configurable threshold

- **New Services**
  - `ImportService` - CSV/JSON quote import with entity creation
  - `ExportService` - CSV/Markdown export for quotes, products, vendors
  - `BackupService` - Database backup, restore, and listing
  - `DeduplicationService` - Find similar entities and merge them

- **Tests** - 25 new tests for data management (165 total tests)

## [0.1.5]

### Added
- **Workflow Features** - Support the full purchasing lifecycle
  - **Purchase Lists** - Group quotes into named shopping lists
    - Create lists: `buylog purchase-list create "My List" --description "Weekend shopping"`
    - Add quotes: `buylog purchase-list add "My List" 123`
    - View list: `buylog purchase-list show "My List"`
    - Total value calculation for each list
  - **Status Tracking** - Mark quotes as "considering", "ordered", "received"
    - Set status: `buylog status set 123 ordered`
    - List by status: `buylog status list ordered`
    - Color-coded status in TUI (cyan/yellow/green)
  - **Notes** - Add freeform notes to any entity
    - Add note: `buylog note add product 1 "Great product!"`
    - List notes: `buylog note list product 1`
  - **Tags** - Categorize entities with tags
    - Add tag: `buylog tag add "sale" product 1`
    - Search by tag: `buylog tag search "sale"`
  - **Watchlist** - Track products for price monitoring
    - Add to watchlist: `buylog watchlist add "iPhone 15" --target-price 800`
    - View watchlist: `buylog watchlist list`

- **TUI Enhancements for Workflow**
  - New **Lists** tab for managing purchase lists (Ctrl+7)
  - New **Watchlist** tab for monitoring products (Ctrl+8)
  - **Status column** in Quotes tab with color coding
  - Press `t` to set quote status
  - Press `w` to add product to watchlist

- **New Models**
  - `PurchaseList` - Named shopping lists with quote associations
  - `Note` - Polymorphic notes attachable to any entity
  - `Tag` and `EntityTag` - Flexible tagging system
  - `Watchlist` - Product monitoring with target prices

- **New Services**
  - `PurchaseListService` - List CRUD, add/remove quotes
  - `NoteService` - Note CRUD for any entity
  - `TagService` - Tag management and entity tagging
  - `WatchlistService` - Watchlist management

- **Tests** - 40 new tests for workflow features (140 total tests)

## [0.1.4]

### Added
- **Price Comparison** - Compare prices across vendors for better purchasing decisions
  - Compare by exact product name: `buylog compare --product "iPhone 15"`
  - Compare by search term: `buylog compare --search "iPhone"` (matches all iPhone models)
  - Compare by category: `buylog compare --category "Mobile Phones"`
  - Compare by brand: `buylog compare --brand "Apple"`
  - Shows best/worst prices, average, and potential savings
  - CLI commands for all comparison types

- **TUI Comparison Modal** - Press `c` to open comparison dialog
  - Dropdown to select comparison type (Product, Search, Category, Brand)
  - Dynamic input field changes based on selection
  - Dropdown for Product/Category/Brand, text input for Search
  - Results displayed with color-coded best/worst prices

- **Product Categories** - Organize products by type
  - New `category` field on Product model
  - Set categories: `buylog category set "iPhone 15" "Mobile Phones"`
  - List categories: `buylog category list`
  - Seed data includes categories (Mobile Phones, Laptops, Tablets, etc.)

- **ComparisonService** - New service for price comparison logic
  - `compare_product()` - Compare prices for a single product
  - `compare_by_search()` - Compare products matching a search term
  - `compare_by_category()` - Compare products in a category
  - `compare_by_brand()` - Compare products from a brand
  - `get_categories()` - List all product categories
  - `set_product_category()` - Set/update product category

- **Tests** - 12 new tests for comparison functionality (100 total tests)

## [0.1.3]

### Added
- **TUI Enhancements** - Improved daily usability
  - **Tab Switching** - `Ctrl+1-6` to switch tabs directly
  - **Vim-style Navigation** - `j/k` for rows, `h/l` for tabs
  - **Column Sorting** - Click column headers or press `1-7` to sort
  - **Quick Filters** - Press `f` to filter quotes by vendor, brand, or price range
  - **Inline Editing** - Press `e` to edit selected entity
  - **Sparklines** - Mini price trend graphs in quote rows showing price history

## [0.1.2]

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
  - `buylog alert add <product> <threshold>` - Create price alert
  - `buylog alert list [--triggered]` - List all or triggered alerts
  - `buylog alert deactivate <id>` - Deactivate an alert
  - `buylog history --product <name>` - View product price history
  - `buylog history --quote-id <id>` - View quote price history
  - Extended `buylog add` with `--shipping` and `--tax-rate` options

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

## [0.1.1]

### Added
- **Textual TUI** - Interactive terminal user interface (`buylog tui`)
  - Tabbed interface for Brands, Products, Vendors, Quotes, and Forex
  - DataTables with row selection and keyboard navigation
  - Modal forms for adding new entities
  - Delete confirmation dialogs
  - Search/filter functionality across all tables
  - Keyboard shortcuts (q=quit, a=add, d=delete, r=refresh, s=search)
- **Database seeding** - `buylog seed` command to populate sample data
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

## [0.1.0]

### Added
- Command Line Interface with CRUD operations
- SQLAlchemy ORM models (Brand, Product, Vendor, Quote, Forex)
- Service layer with business logic separation
- Multi-currency support with forex conversion
- Audit logging for entity changes
- pytest test suite with Factory Boy
