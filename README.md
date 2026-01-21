# buyer-log

A Python tool for purchasing support and vendor quote management with CLI and TUI interfaces.

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

```bash
# Clone the repository
git clone <repo-url>
cd buyer-log

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
buyer add --brand apple
buyer add --brand apple --product iphone-14
buyer add --vendor amazon.com --currency USD
buyer add --vendor amazon.com --product iphone-14 --quote 600

# Add forex rates
buyer add-fx --code EUR --usd-per-unit 1.085
buyer add-fx --code GBP --usd-per-unit 1.27 --date 2025-01-15

# Add quotes with shipping and tax
buyer add --vendor amazon.com --product iphone-14 --quote 600 --shipping 10.00 --tax-rate 8.5

# List entities
buyer list brands
buyer list products
buyer list vendors
buyer list quotes
buyer list brands --filter apple

# Search across entities
buyer search iphone

# Update entities
buyer update brand apple --new-name Apple
buyer update product iphone-14 --new-name "iPhone 14"

# Delete entities
buyer delete brand --name apple
buyer delete product --name iphone-14
buyer delete vendor --name amazon.com
buyer delete quote --id 1

# Seed database with sample data
buyer seed

# Price alerts
buyer alert add "iPhone 15 Pro" 900      # Create alert when price drops to $900
buyer alert list                          # List all alerts
buyer alert list --triggered              # List triggered alerts only
buyer alert deactivate 1                  # Deactivate alert by ID

# Price history
buyer history --product "iPhone 15 Pro"   # View price history for a product
buyer history --quote-id 1                # View price history for a specific quote

# Price comparison
buyer compare --product "iPhone 15 Pro"   # Compare prices for a specific product
buyer compare --search "iPhone"           # Compare all products matching search term
buyer compare --category "Mobile Phones"  # Compare all products in a category
buyer compare --brand "Apple"             # Compare all products from a brand

# Product categories
buyer category set "iPhone 15 Pro" "Mobile Phones"  # Set product category
buyer category list                                  # List all categories

# Purchase lists
buyer purchase-list create "My List" --description "Weekend shopping"
buyer purchase-list add "My List" 123               # Add quote to list
buyer purchase-list remove "My List" 123            # Remove quote from list
buyer purchase-list show "My List"                  # Show list contents
buyer purchase-list all                             # List all purchase lists
buyer purchase-list delete "My List"                # Delete a list

# Quote status tracking
buyer status set 123 considering                    # Set quote status
buyer status set 123 ordered                        # Mark as ordered
buyer status set 123 received                       # Mark as received
buyer status list ordered                           # List quotes by status

# Notes
buyer note add product 1 "Great product!"           # Add note to product
buyer note add vendor 1 "Fast shipping"             # Add note to vendor
buyer note list product 1                           # List notes for product
buyer note delete 1                                 # Delete note by ID

# Tags
buyer tag add "sale" product 1                      # Tag a product
buyer tag add "priority" quote 123                  # Tag a quote
buyer tag remove "sale" product 1                   # Remove tag
buyer tag list                                      # List all tags
buyer tag list --entity-type product --entity-id 1  # List tags for entity
buyer tag search "sale"                             # Find entities by tag

# Watchlist
buyer watchlist add "iPhone 15" --target-price 800  # Add to watchlist
buyer watchlist list                                # List active watchlist
buyer watchlist list --all                          # Include inactive items
buyer watchlist update 1 --target-price 750         # Update target price
buyer watchlist remove 1                            # Remove from watchlist

# Import data
buyer import quotes data.csv                        # Import quotes from CSV
buyer import quotes data.json                       # Import quotes from JSON
buyer import quotes data.csv --no-create            # Don't create missing entities

# Export data
buyer export quotes --format csv --file quotes.csv   # Export to CSV
buyer export quotes --format markdown --file report.md  # Export to Markdown
buyer export quotes --filter "iPhone"               # Export filtered quotes
buyer export products --file products.csv           # Export products
buyer export vendors --file vendors.csv             # Export vendors

# Backup and restore
buyer backup                                        # Create timestamped backup
buyer backup --output my-backup.db                  # Custom backup path
buyer restore my-backup.db                          # Restore from backup
buyer restore my-backup.db --no-backup              # Restore without backing up current
buyer backups                                       # List available backups

# Find and merge duplicates
buyer duplicates vendors                            # Find similar vendors
buyer duplicates vendors --threshold 0.7            # Custom similarity threshold
buyer duplicates products                           # Find similar products
buyer duplicates merge-vendors 1 2 3                # Merge vendors 2,3 into vendor 1
buyer duplicates merge-products 1 2 3               # Merge products 2,3 into product 1

# Clipboard support
buyer clipboard quote 123                           # Copy quote to clipboard
buyer clipboard product "iPhone 15 Pro"             # Copy product to clipboard
buyer clipboard vendor "Amazon US"                  # Copy vendor to clipboard

# Vendor URL management
buyer vendor-url set "Amazon US" "https://amazon.com"  # Set vendor URL
buyer vendor-url open "Amazon US"                   # Open vendor URL in browser
buyer vendor-url clear "Amazon US"                  # Clear vendor URL

# Receipt attachments
buyer receipt attach 123 receipt.pdf                # Attach receipt to quote
buyer receipt open 123                              # Open attached receipt
buyer receipt detach 123                            # Remove receipt from quote
buyer receipt list                                  # List quotes with receipts

# Web scraping
buyer scrape url "https://example.com/product"      # Scrape price from URL
buyer scrape quote "https://example.com/product" --vendor "Amazon US" --product "iPhone 15"  # Create quote from URL
```

### Text User Interface (TUI)

Launch the interactive TUI:

```bash
buyer tui
```

The TUI provides:
- Tabbed interface for Brands, Products, Vendors, Quotes, Forex rates, Alerts, Lists, and Watchlist
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
  - `Ctrl+1-8` - Switch tabs directly
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
uv run pytest --cov-report=html:cov_html --cov-report=term-missing --cov=buyer
```

### Generate ER Diagram

```bash
make diagram
# or
uv run python src/buyer/models.py

# Output: doc/er_model.svg
```

### Clean Build Artifacts

```bash
make clean
```

## Architecture

### Project Structure

```
buyer-log/
├── src/buyer/           # Main package
│   ├── models.py        # SQLAlchemy ORM models
│   ├── cli.py           # CLI interface
│   ├── tui.py           # Textual TUI interface
│   ├── services.py      # Business logic layer
│   ├── config.py        # Configuration management
│   ├── audit.py         # Audit logging
│   └── cache.py         # Caching utilities
├── tests/               # Test suite
│   ├── conftest.py      # pytest fixtures
│   ├── factories.py     # Factory Boy test data
│   ├── test_models.py   # Model tests
│   ├── test_services.py # Service layer tests
│   └── test_quote_analysis.py # Quote analysis feature tests
├── doc/                 # Documentation
│   └── er_model.svg     # Auto-generated ER diagram
└── pyproject.toml       # Project dependencies
```

### Data Model

The core domain models:

- **Vendor** - Selling entities with currency, discount codes, and brand relationships
- **Brand** - Manufacturing entities linked to products and vendors
- **Product** - Items with brand associations that can be quoted by vendors
- **Quote** - Price quotes from vendors with shipping, tax, status, and total cost calculation
- **QuoteHistory** - Price change tracking for quotes (create/update events)
- **PriceAlert** - Price threshold alerts for products
- **Forex** - Currency exchange rates for multi-currency support
- **PurchaseList** - Named shopping lists grouping quotes
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
- `VendorService` - Vendor operations
- `QuoteService` - Quote management with currency conversion, best price detection, price updates, and status tracking
- `QuoteHistoryService` - Price history tracking and trend computation
- `PriceAlertService` - Price alert creation, triggering, and management
- `ComparisonService` - Price comparison by product, search, category, or brand
- `PurchaseListService` - Purchase list CRUD, add/remove quotes
- `NoteService` - Note CRUD for any entity type
- `TagService` - Tag management and entity tagging
- `WatchlistService` - Watchlist management with target prices
- `AuditService` - Entity change tracking

## Technologies

- **Python 3.13+** - Core language
- **SQLAlchemy 2.0+** - ORM and database abstraction
- **Textual** - Modern terminal UI framework
- **pytest** - Testing framework
- **Factory Boy** - Test data generation
- **uv** - Fast Python package manager
- **eralchemy** - ER diagram generation
- **tabulate** - CLI table formatting

## Configuration

The application uses a configuration system via `config.py`:
- Database path: `~/.buyer/buyer.db` (configurable via `BUYER_DB_PATH`)
- Log level: `INFO` by default (configurable via `BUYER_LOG_LEVEL`)
- Logging: Configured for both file and console output

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
