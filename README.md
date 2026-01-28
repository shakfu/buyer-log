# buylog

A Python tool to help you keep track of what you buy and want to buy.

## Features

- **Command Line Interface (CLI)** - Full CRUD operations for managing brands, products, vendors, and quotes
- **Text User Interface (TUI)** - Interactive terminal UI built with Textual
- **Data Persistence** - SQLAlchemy ORM with SQLite support
- **Multi-currency Support** - Forex rate tracking with automatic currency conversion
- **Quote Analysis** - Best price highlighting, price history tracking, and price alerts
- **Service Layer** - Business logic separation with validation and error handling
- **Audit Logging** - Track entity creation, updates, and deletions
- **Testing** - pytest-based test suite with factory pattern

## Installation

```sh
pip install buylog
```

To build

```bash
# Clone the repository
git clone https://github.com/shakfu/buylog
cd buylog

# Install dependencies
uv sync

# Or install with development dependencies
uv sync --group dev
```

## Usage

### Command Line Interface

The CLI supports comprehensive CRUD operations:

```sh
# Add entities
buylog add --brand apple
buylog add --brand apple --product iphone-14
buylog add --vendor amazon.com --currency USD
buylog add --vendor amazon.com --product iphone-14 --quote 600

# Add forex rates
buylog add-fx --code EUR --usd-per-unit 1.085
buylog add-fx --code GBP --usd-per-unit 1.27 --date 2025-01-15

# Add quotes with shipping and tax
buylog add --vendor amazon.com --product iphone-14 --quote 600 --shipping 10.00 --tax-rate 8.5

# List entities
buylog list brands
buylog list products
buylog list vendors
buylog list quotes
buylog list brands --filter apple

# Search across entities
buylog search iphone

# Update entities
buylog update brand apple --new-name Apple
buylog update product iphone-14 --new-name "iPhone 14"

# Delete entities
buylog delete brand --name apple
buylog delete product --name iphone-14
buylog delete vendor --name amazon.com
buylog delete quote --id 1

# Seed database with sample data
buylog seed

# Price alerts
buylog alert add "iPhone 15 Pro" 900      # Create alert when price drops to $900
buylog alert list                          # List all alerts
buylog alert list --triggered              # List triggered alerts only
buylog alert deactivate 1                  # Deactivate alert by ID

# Price history
buylog history --product "iPhone 15 Pro"   # View price history for a product
buylog history --quote-id 1                # View price history for a specific quote

# Price comparison
buylog compare --product "iPhone 15 Pro"   # Compare prices for a specific product
buylog compare --search "iPhone"           # Compare all products matching search term
buylog compare --category "Mobile Phones"  # Compare all products in a category
buylog compare --brand "Apple"             # Compare all products from a brand

# Product categories
buylog category set "iPhone 15 Pro" "Mobile Phones"  # Set product category
buylog category list                                  # List all categories

# Purchase lists
buylog purchase-list create "My List" --description "Weekend shopping"
buylog purchase-list add "My List" 123               # Add quote to list
buylog purchase-list remove "My List" 123            # Remove quote from list
buylog purchase-list show "My List"                  # Show list contents
buylog purchase-list all                             # List all purchase lists
buylog purchase-list delete "My List"                # Delete a list

# Quote status tracking
buylog status set 123 considering                    # Set quote status
buylog status set 123 ordered                        # Mark as ordered
buylog status set 123 received                       # Mark as received
buylog status list ordered                           # List quotes by status

# Notes
buylog note add product 1 "Great product!"           # Add note to product
buylog note add vendor 1 "Fast shipping"             # Add note to vendor
buylog note list product 1                           # List notes for product
buylog note delete 1                                 # Delete note by ID

# Tags
buylog tag add "sale" product 1                      # Tag a product
buylog tag add "priority" quote 123                  # Tag a quote
buylog tag remove "sale" product 1                   # Remove tag
buylog tag list                                      # List all tags
buylog tag list --entity-type product --entity-id 1  # List tags for entity
buylog tag search "sale"                             # Find entities by tag

# Watchlist
buylog watchlist add "iPhone 15" --target-price 800  # Add to watchlist
buylog watchlist list                                # List active watchlist
buylog watchlist list --all                          # Include inactive items
buylog watchlist update 1 --target-price 750         # Update target price
buylog watchlist remove 1                            # Remove from watchlist

# Import data
buylog import quotes data.csv                        # Import quotes from CSV
buylog import quotes data.json                       # Import quotes from JSON
buylog import quotes data.csv --no-create            # Don't create missing entities

# Export data
buylog export quotes --format csv --file quotes.csv   # Export to CSV
buylog export quotes --format markdown --file report.md  # Export to Markdown
buylog export quotes --filter "iPhone"               # Export filtered quotes
buylog export products --file products.csv           # Export products
buylog export vendors --file vendors.csv             # Export vendors

# Backup and restore
buylog backup                                        # Create timestamped backup
buylog backup --output my-backup.db                  # Custom backup path
buylog restore my-backup.db                          # Restore from backup
buylog restore my-backup.db --no-backup              # Restore without backing up current
buylog backups                                       # List available backups

# Find and merge duplicates
buylog duplicates vendors                            # Find similar vendors
buylog duplicates vendors --threshold 0.7            # Custom similarity threshold
buylog duplicates products                           # Find similar products
buylog duplicates merge-vendors 1 2 3                # Merge vendors 2,3 into vendor 1
buylog duplicates merge-products 1 2 3               # Merge products 2,3 into product 1

# Clipboard support
buylog clipboard quote 123                           # Copy quote to clipboard
buylog clipboard product "iPhone 15 Pro"             # Copy product to clipboard
buylog clipboard vendor "Amazon US"                  # Copy vendor to clipboard

# Vendor URL management
buylog vendor-url set "Amazon US" "https://amazon.com"  # Set vendor URL
buylog vendor-url open "Amazon US"                   # Open vendor URL in browser
buylog vendor-url clear "Amazon US"                  # Clear vendor URL

# Receipt attachments
buylog receipt attach 123 receipt.pdf                # Attach receipt to quote
buylog receipt open 123                              # Open attached receipt
buylog receipt detach 123                            # Remove receipt from quote
buylog receipt list                                  # List quotes with receipts

# Web scraping
buylog scrape url "https://example.com/product"      # Scrape price from URL
buylog scrape quote "https://example.com/product" --vendor "Amazon US" --product "iPhone 15"  # Create quote from URL

# HTML reports
buylog report price-comparison                       # Compare prices across vendors
buylog report price-comparison --filter "iPhone"     # Filter by product name
buylog report price-comparison --output report.html  # Save to file
buylog report purchase-summary --output summary.html # Summary by status
buylog report vendor-analysis --output vendors.html  # Vendor statistics

# Excel export
buylog export -t vendors -o vendors.xlsx             # Export vendors to Excel
buylog export -t quotes -o quotes.xlsx               # Export quotes to Excel
buylog export -o database.xlsx                       # Export all tables to single file
buylog export                                        # Export all to buylog-db.xlsx (default)

# Excel import
buylog import vendors.xlsx -t vendors                # Import vendors from Excel
buylog import products.xlsx -t products              # Import products from Excel
buylog import quotes.xlsx -t quotes                  # Import quotes from Excel
buylog import specs.xlsx -t specifications           # Import specifications from Excel
buylog import pos.xlsx -t purchase_orders            # Import purchase orders from Excel

# Generate import templates
buylog template -t vendors -f xlsx                   # Excel template: vendors-template.xlsx
buylog template -t vendors -f yaml                   # YAML template: vendors-template.yaml
buylog template -t specs -f json                     # JSON template: specifications-template.json
buylog template -t products -f xlsx                  # Excel template with brand dropdown
buylog template -t purchase_orders -f xlsx           # PO template with vendor/product dropdowns

# Purchase orders
buylog po create PO-001 --vendor "Amazon" --product "iPhone 15" --price 999.99
buylog po create PO-002 --vendor "Amazon" --product "iPhone 15" --price 999.99 --quantity 2
buylog po list                                       # List all purchase orders
buylog po list --status pending                      # Filter by status
buylog po update PO-001 --status ordered             # Update status
buylog po update PO-001 --status received            # Mark as received

# Specifications
buylog spec create "Camera Spec" --description "For camera products"
buylog spec add-feature "Camera Spec" "Resolution" --type number --unit "MP"
buylog spec add-feature "Camera Spec" "Has WiFi" --type boolean
buylog spec list                                     # List all specifications
buylog spec show "Camera Spec"                       # Show spec with features

# Database migration
buylog migrate                                       # Apply pending schema migrations
buylog migrate --dry-run                             # Preview SQL without executing
```

### Text User Interface (TUI)

Launch the interactive TUI:

```bash
buylog tui
```

The TUI provides:

- Tabbed interface for Brands, Products, Vendors, Quotes, Forex rates, Alerts, Lists, Watchlist, Purchase Orders, and Specifications
- DataTables with row selection
- Modal forms for adding entities
- Search/filter functionality
- **Quote Analysis Features**:
  - Best prices highlighted in green
  - Total cost calculation (with discount, shipping, tax)
  - Price trend indicators (^ up, v down, - stable, * new)
  - Sparkline mini-graphs showing price history
  - Triggered alerts highlighted in yellow
  - **Status column** with color coding (considering=cyan, ordered=yellow, received=green)
- **Workflow Features**:
  - **Lists tab** - View and manage purchase lists
  - **Watchlist tab** - Monitor products with target prices
  - Set quote status with `t` key
  - Add to watchlist with `w` key
- **Integration Features**:
  - **URL column** in Vendors tab showing link indicators
  - Copy to clipboard with `y` key (quotes, products, vendors)
  - Open vendor URL with `o` key (on Vendors tab)
- **Quick Filters** for quotes by vendor, brand, or price range
- **Inline Editing** - Edit entities directly with `e` key
- **Column Sorting** - Click headers or press number keys to sort
- **Price Comparison** - Compare prices with `c` key (select type: Product/Search/Category/Brand)
- Keyboard shortcuts:
  - `q` - Quit
  - `a` - Add new entity
  - `c` - Compare prices
  - `d` - Delete selected entity
  - `e` - Edit selected entity
  - `f` - Filter quotes
  - `o` - Open vendor URL (vendors tab)
  - `r` - Refresh data
  - `s` or `/` - Focus search
  - `t` - Set quote status
  - `w` - Add to watchlist
  - `y` - Copy to clipboard
  - `Ctrl+1-0` - Switch tabs directly (1-9 and 0 for tab 10)
  - `h/l` - Previous/next tab (vim-style)
  - `j/k` - Move cursor down/up (vim-style)
  - `1-7` - Sort by column number

## Development

### Running Tests

```bash
# Run all tests
make test
# or
uv run pytest

# Run with coverage report
make coverage
# or
uv run pytest --cov-report=html:cov_html --cov-report=term-missing --cov=buylog
```

### Generate ER Diagram

```bash
make diagram
# or
uv run python src/buylog/models.py

# Output: doc/er_model.svg
```

### Clean Build Artifacts

```bash
make clean
```

## Architecture

### Project Structure

```text
buylog/
├── src/buylog/          # Main package
│   ├── models.py        # SQLAlchemy ORM models
│   ├── cli.py           # CLI interface
│   ├── tui.py           # Textual TUI interface
│   ├── services.py      # Business logic layer
│   ├── excel.py         # Excel import/export (openpyxl)
│   ├── templates.py     # YAML/JSON template generation
│   ├── migrate.py       # Database schema migration
│   ├── config.py        # Configuration management
│   ├── audit.py         # Audit logging
│   └── cache.py         # Caching utilities
├── tests/               # Test suite
│   ├── conftest.py      # pytest fixtures
│   ├── factories.py     # Factory Boy test data
│   ├── test_models.py   # Model tests
│   ├── test_services.py # Service layer tests
│   ├── test_excel.py    # Excel import/export tests
│   └── test_quote_analysis.py # Quote analysis feature tests
├── doc/                 # Documentation
│   └── er_model.svg     # Auto-generated ER diagram
└── pyproject.toml       # Project dependencies
```

### Data Model

The core domain models:

- **Vendor** - Selling entities with currency, discount codes, contact info, and address
- **Brand** - Manufacturing entities linked to products and vendors
- **Product** - Items with brand associations and optional specification links
- **Quote** - Price quotes from vendors with shipping, tax, status, and total cost calculation
- **QuoteHistory** - Price change tracking for quotes (create/update events)
- **PriceAlert** - Price threshold alerts for products
- **Forex** - Currency exchange rates for multi-currency support
- **PurchaseList** - Named shopping lists grouping quotes
- **PurchaseOrder** - Committed purchases with status tracking and delivery dates
- **Specification** - Structured product attribute definitions
- **SpecificationFeature** - Feature definitions with data types and validation
- **ProductFeature** - Feature values for products
- **Note** - Freeform notes attachable to any entity (polymorphic)
- **Tag** - Categorization tags with optional color
- **EntityTag** - Junction table for tagging any entity
- **Watchlist** - Product monitoring with target prices

Key relationships:

- Many-to-many between Vendors and Brands (via `vendor_brand` junction table)
- One-to-many from Brand to Products
- One-to-many from Vendor and Product to Quotes
- One-to-many from Quote to QuoteHistory
- One-to-many from Product to PriceAlert
- Many-to-many between PurchaseList and Quotes (via `purchase_list_quote` junction table)
- One-to-many from Product to Watchlist

See the auto-generated ER diagram: `doc/er_model.svg`

### Service Layer

Business logic is separated into service classes:

- `BrandService` - Brand CRUD with validation
- `ProductService` - Product management with eager loading
- `VendorService` - Vendor operations with extended contact/address fields
- `QuoteService` - Quote management with currency conversion, best price detection, price updates, and status tracking
- `QuoteHistoryService` - Price history tracking and trend computation
- `PriceAlertService` - Price alert creation, triggering, and management
- `ComparisonService` - Price comparison by product, search, category, or brand
- `PurchaseListService` - Purchase list CRUD, add/remove quotes
- `PurchaseOrderService` - Purchase order CRUD, status transitions, create from quote
- `SpecificationService` - Specification and feature management
- `ProductFeatureService` - Product feature value management
- `NoteService` - Note CRUD for any entity type
- `TagService` - Tag management and entity tagging
- `WatchlistService` - Watchlist management with target prices
- `ReportService` - HTML report generation (price comparison, purchase summary, vendor analysis)
- `AuditService` - Entity change tracking

## Technologies

- **Python 3.13+** - Core language
- **SQLAlchemy 2.0+** - ORM and database abstraction
- **Textual** - Modern terminal UI framework
- **openpyxl** - Excel file read/write
- **pytest** - Testing framework
- **Factory Boy** - Test data generation
- **uv** - Fast Python package manager
- **eralchemy** - ER diagram generation
- **tabulate** - CLI table formatting

## Configuration

The application uses a configuration system via `config.py`:

- Database path: `~/.buylog/buylog.db` (configurable via `BUYER_DB_PATH`)
- Log level: `INFO` by default (configurable via `BUYER_LOG_LEVEL`)
- Logging: Configured for both file and console output

## License

MIT

## Contributing

Feedback, bug reports and code contributions are welcome!
