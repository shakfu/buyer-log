# TODO

## Priority 1: Quote Analysis

Core value proposition - help users make better purchasing decisions.

- [x] **Best price highlight** - Auto-highlight lowest quote per product across vendors
- [x] **Total cost calculator** - Factor in shipping, taxes, discounts for true comparison
- [x] **Price history** - Track quote changes over time, show trends in TUI
- [x] **Price alerts** - Flag when a quote drops below a user-defined threshold

## Priority 2: TUI Enhancements

Improve daily usability of the interface.

- [ ] **Tab switching** - Ctrl+1/2/3/4/5 or Cmd+1/2/3/4/5 to switch tabs
- [ ] **Vim-style navigation** - j/k for rows, h/l for tabs
- [ ] **Column sorting** - Press key or click column header to sort
- [ ] **Quick filters** - Filter quotes by vendor, brand, or price range
- [ ] **Inline editing** - Edit cells directly in the table
- [ ] **Sparklines** - Mini price trend graphs in quote rows

## Priority 3: Workflow

Support the full purchasing lifecycle.

- [ ] **Purchase lists** - Group quotes into named shopping lists
- [ ] **Status tracking** - Mark quotes as "considering", "ordered", "received"
- [ ] **Notes/tags** - Add freeform notes or tags to any entity
- [ ] **Watchlist** - Track specific products for price monitoring

## Priority 4: Data Management

Import, export, and maintain data integrity.

- [ ] **CSV/JSON import** - Bulk import quotes from spreadsheets
- [ ] **Export reports** - Export filtered views to CSV/PDF
- [ ] **Backup/restore** - Simple database backup command (`buyer backup`, `buyer restore`)
- [ ] **Merge duplicates** - Detect and merge similar vendors/products

## Priority 5: Integration

Connect with external tools and data.

- [ ] **Clipboard support** - Copy selected quote/product to clipboard
- [ ] **URL field for vendors** - Store and open vendor URLs
- [ ] **Receipt attachment** - Link to receipt files after purchase
- [ ] **Web scraping** - Fetch product price from a URL

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
