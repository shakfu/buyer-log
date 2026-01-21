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
```

### Text User Interface (TUI)

Launch the interactive TUI:

```bash
buyer tui
```

The TUI provides:
- Tabbed interface for Brands, Products, Vendors, Quotes, Forex rates, and Alerts
- DataTables with row selection
- Modal forms for adding entities
- Search/filter functionality
- **Quote Analysis Features**:
  - Best prices highlighted in green
  - Total cost calculation (with discount, shipping, tax)
  - Price trend indicators (^ up, v down, - stable, * new)
  - Triggered alerts highlighted in yellow
- Keyboard shortcuts:
  - `q` - Quit
  - `a` - Add new entity
  - `d` - Delete selected entity
  - `r` - Refresh data
  - `s` or `/` - Focus search

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
- **Quote** - Price quotes from vendors with shipping, tax, and total cost calculation
- **QuoteHistory** - Price change tracking for quotes (create/update events)
- **PriceAlert** - Price threshold alerts for products
- **Forex** - Currency exchange rates for multi-currency support

Key relationships:
- Many-to-many between Vendors and Brands (via `vendor_brand` junction table)
- One-to-many from Brand to Products
- One-to-many from Vendor and Product to Quotes
- One-to-many from Quote to QuoteHistory
- One-to-many from Product to PriceAlert

See the auto-generated ER diagram: `doc/er_model.svg`

### Service Layer

Business logic is separated into service classes:
- `BrandService` - Brand CRUD with validation
- `ProductService` - Product management with eager loading
- `VendorService` - Vendor operations
- `QuoteService` - Quote management with currency conversion, best price detection, and price updates
- `QuoteHistoryService` - Price history tracking and trend computation
- `PriceAlertService` - Price alert creation, triggering, and management
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
