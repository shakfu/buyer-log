# TODO

## Priority 1: Quote Analysis

Core value proposition - help users make better purchasing decisions.

- [x] **Best price highlight** - Auto-highlight lowest quote per product across vendors
- [x] **Total cost calculator** - Factor in shipping, taxes, discounts for true comparison
- [x] **Price history** - Track quote changes over time, show trends in TUI
- [x] **Price alerts** - Flag when a quote drops below a user-defined threshold

## Priority 2: TUI Enhancements

Improve daily usability of the interface.

- [x] **Tab switching** - Ctrl+1/2/3/4/5/6 to switch tabs
- [x] **Vim-style navigation** - j/k for rows, h/l for tabs
- [x] **Column sorting** - Press number key or click column header to sort
- [x] **Quick filters** - Filter quotes by vendor, brand, or price range
- [x] **Inline editing** - Edit entities with `e` key
- [x] **Sparklines** - Mini price trend graphs in quote rows
- [x] **Price comparison** - Compare prices by product, search, category, or brand

## Priority 3: Workflow

Support the full purchasing lifecycle.

- [x] **Purchase lists** - Group quotes into named shopping lists
- [x] **Status tracking** - Mark quotes as "considering", "ordered", "received"
- [x] **Notes/tags** - Add freeform notes or tags to any entity
- [x] **Watchlist** - Track specific products for price monitoring

## Priority 4: Data Management

Import, export, and maintain data integrity.

- [x] **CSV/JSON import** - Bulk import quotes from spreadsheets
- [x] **Export reports** - Export filtered views to CSV, Markdown
- [x] **Backup/restore** - Simple database backup command (`buyer backup`, `buyer restore`)
- [x] **Merge duplicates** - Detect and merge similar vendors/products

## Priority 5: Integration

Connect with external tools and data.

- [x] **Clipboard support** - Copy selected quote/product to clipboard
- [x] **URL field for vendors** - Store and open vendor URLs
- [x] **Receipt attachment** - Link to receipt files after purchase
- [x] **Web scraping** - Fetch product price from a URL

## Completed

### CLI Enhancements

- [x] **`add` command:**
  - [x] Allow simultaneous addition of a product and a new brand
  - [x] Prompt to add missing products or vendors when creating a quote
  - [x] Integrate the `Forex` model for currency conversion
- [x] **`delete` command:**
  - [x] Implement `delete` command for removing brands, products, vendors, and quotes
  - [x] Delete quotes by ID
- [x] **`update` command:**
  - [x] Implement `update` command for modifying brands, products, and vendors
- [x] **`list` command:**
  - [x] Add filtering and sorting options
  - [x] Format output as tables
- [x] **`search` command:**
  - [x] Implement `search` command to find items

### TUI

- [x] **Textual TUI** - Interactive terminal interface (`buyer tui`)
- [x] **Database seeding** - Sample data command (`buyer seed`)

### TUI Enhancements (v0.4.0)

- [x] **Tab switching** - `Ctrl+1-6` to switch tabs directly
- [x] **Vim-style navigation** - `j/k` for rows, `h/l` for tabs
- [x] **Column sorting** - Click headers or press `1-7` to sort
- [x] **Quick filters** - Press `f` to filter quotes by vendor, brand, or price range
- [x] **Inline editing** - Press `e` to edit selected entity
- [x] **Sparklines** - Mini price trend graphs in quote rows

### Price Comparison (v0.5.0)

- [x] **Compare by product** - Exact product match across vendors
- [x] **Compare by search** - Partial match for product names
- [x] **Compare by category** - All products in a category
- [x] **Compare by brand** - All products from a brand
- [x] **Product categories** - Organize products by type (Mobile Phones, Laptops, etc.)
- [x] **TUI comparison modal** - Press `c` with dropdown to select comparison type

### Workflow Features (v0.6.0)

- [x] **Purchase lists** - Group quotes into named shopping lists
- [x] **Status tracking** - Mark quotes as "considering", "ordered", "received"
- [x] **Notes** - Add freeform notes to any entity (product, vendor, quote, brand)
- [x] **Tags** - Categorize entities with tags
- [x] **Watchlist** - Track specific products for price monitoring
- [x] **TUI Lists tab** - View and manage purchase lists (`Ctrl+7`)
- [x] **TUI Watchlist tab** - Monitor products with target prices (`Ctrl+8`)
- [x] **TUI status column** - Color-coded quote status in Quotes tab
- [x] **Set status keybinding** - Press `t` to set quote status
- [x] **Watchlist keybinding** - Press `w` to add to watchlist

### Data Management (v0.7.0)

- [x] **CSV import** - Import quotes from CSV files with auto-entity creation
- [x] **JSON import** - Import quotes from JSON files
- [x] **CSV export** - Export quotes, products, vendors to CSV
- [x] **Markdown export** - Export quotes to Markdown reports with summary
- [x] **Database backup** - Create timestamped backups (`buyer backup`)
- [x] **Database restore** - Restore from backup (`buyer restore`)
- [x] **Backup listing** - List available backups (`buyer backups`)
- [x] **Find duplicates** - Detect similar vendors/products using Jaccard similarity
- [x] **Merge vendors** - Merge duplicate vendors, reassigning quotes
- [x] **Merge products** - Merge duplicate products, reassigning quotes

### Integration Features (v0.8.0)

- [x] **Clipboard support** - Copy quote/product/vendor to clipboard (`y` key in TUI)
- [x] **Vendor URL field** - Store vendor URLs with `buyer vendor-url set/open/clear`
- [x] **TUI URL column** - Show link indicators in vendors table
- [x] **Open URL keybinding** - Press `o` to open vendor URL in browser
- [x] **Receipt attachment** - Attach receipt files to quotes (`buyer receipt attach/open/detach`)
- [x] **Receipt listing** - List quotes with receipts (`buyer receipt list`)
- [x] **Web scraping** - Scrape prices from URLs (`buyer scrape url/quote`)
- [x] **Auto vendor URL** - Set vendor URL from scraped page base URL
