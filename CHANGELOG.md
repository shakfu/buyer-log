# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
