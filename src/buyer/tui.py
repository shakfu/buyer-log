"""Textual TUI interface for buyer tool"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Static,
    TabbedContent,
    TabPane,
)
from sqlalchemy import select
from sqlalchemy.orm import Session as SessionType

from .config import Config
from .models import Base, Brand, Product, Vendor, Quote, Forex
from .services import (
    BrandService,
    ProductService,
    VendorService,
    QuoteService,
    DuplicateError,
    ValidationError,
)


# Database setup
engine = Config.get_engine()
Base.metadata.create_all(engine)
Session = Config.get_session_maker()


class AddBrandModal(ModalScreen[str | None]):
    """Modal for adding a new brand."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-dialog"):
            yield Label("Add Brand", id="modal-title")
            yield Input(placeholder="Brand name", id="brand-name")
            with Horizontal(id="modal-buttons"):
                yield Button("Add", variant="primary", id="add-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-btn":
            name_input = self.query_one("#brand-name", Input)
            self.dismiss(name_input.value)
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def action_cancel(self) -> None:
        self.dismiss(None)


class AddProductModal(ModalScreen[tuple[str, str] | None]):
    """Modal for adding a new product."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-dialog"):
            yield Label("Add Product", id="modal-title")
            yield Input(placeholder="Brand name", id="brand-name")
            yield Input(placeholder="Product name", id="product-name")
            with Horizontal(id="modal-buttons"):
                yield Button("Add", variant="primary", id="add-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-btn":
            brand = self.query_one("#brand-name", Input).value
            product = self.query_one("#product-name", Input).value
            self.dismiss((brand, product))
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class AddVendorModal(ModalScreen[tuple[str, str, str, float] | None]):
    """Modal for adding a new vendor."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-dialog"):
            yield Label("Add Vendor", id="modal-title")
            yield Input(placeholder="Vendor name", id="vendor-name")
            yield Input(placeholder="Currency (default: USD)", id="currency")
            yield Input(placeholder="Discount code (optional)", id="discount-code")
            yield Input(placeholder="Discount % (default: 0)", id="discount")
            with Horizontal(id="modal-buttons"):
                yield Button("Add", variant="primary", id="add-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-btn":
            name = self.query_one("#vendor-name", Input).value
            currency = self.query_one("#currency", Input).value or "USD"
            discount_code = self.query_one("#discount-code", Input).value or None
            discount_str = self.query_one("#discount", Input).value
            discount = float(discount_str) if discount_str else 0.0
            self.dismiss((name, currency, discount_code, discount))
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class AddQuoteModal(ModalScreen[tuple[str, str, str, float] | None]):
    """Modal for adding a new quote."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-dialog"):
            yield Label("Add Quote", id="modal-title")
            yield Input(placeholder="Vendor name", id="vendor-name")
            yield Input(placeholder="Product name", id="product-name")
            yield Input(placeholder="Brand name (if new product)", id="brand-name")
            yield Input(placeholder="Price", id="price")
            with Horizontal(id="modal-buttons"):
                yield Button("Add", variant="primary", id="add-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-btn":
            vendor = self.query_one("#vendor-name", Input).value
            product = self.query_one("#product-name", Input).value
            brand = self.query_one("#brand-name", Input).value or None
            price_str = self.query_one("#price", Input).value
            try:
                price = float(price_str) if price_str else 0.0
                self.dismiss((vendor, product, brand, price))
            except ValueError:
                self.notify("Invalid price", severity="error")
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class AddForexModal(ModalScreen[tuple[str, float, str | None] | None]):
    """Modal for adding a forex rate."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-dialog"):
            yield Label("Add Forex Rate", id="modal-title")
            yield Input(placeholder="Currency code (e.g., EUR)", id="code")
            yield Input(placeholder="USD per unit (e.g., 1.085)", id="rate")
            yield Input(placeholder="Date (YYYY-MM-DD, optional)", id="date")
            with Horizontal(id="modal-buttons"):
                yield Button("Add", variant="primary", id="add-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-btn":
            code = self.query_one("#code", Input).value.upper()
            rate_str = self.query_one("#rate", Input).value
            date_str = self.query_one("#date", Input).value or None
            try:
                rate = float(rate_str) if rate_str else 0.0
                self.dismiss((code, rate, date_str))
            except ValueError:
                self.notify("Invalid rate", severity="error")
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class ConfirmDeleteModal(ModalScreen[bool]):
    """Modal for confirming deletion."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, entity_type: str, name: str) -> None:
        super().__init__()
        self.entity_type = entity_type
        self.entity_name = name

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-dialog"):
            yield Label("Confirm Delete", id="modal-title")
            yield Label(f"Delete {self.entity_type} '{self.entity_name}'?")
            with Horizontal(id="modal-buttons"):
                yield Button("Delete", variant="error", id="delete-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "delete-btn")

    def action_cancel(self) -> None:
        self.dismiss(False)


class BuyerApp(App):
    """Buyer TUI Application."""

    CSS = """
    #modal-dialog {
        width: 60;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: thick $primary;
    }

    #modal-title {
        text-style: bold;
        margin-bottom: 1;
    }

    #modal-buttons {
        margin-top: 1;
        height: 3;
    }

    #modal-buttons Button {
        margin-right: 1;
    }

    Input {
        margin-bottom: 1;
    }

    #search-bar {
        height: 3;
        padding: 0 1;
    }

    #search-input {
        width: 1fr;
    }

    DataTable {
        height: 1fr;
    }

    .tab-content {
        height: 1fr;
    }

    #status-bar {
        height: 1;
        padding: 0 1;
        background: $primary;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("a", "add", "Add"),
        Binding("d", "delete", "Delete"),
        Binding("r", "refresh", "Refresh"),
        Binding("s", "search", "Search"),
        Binding("/", "focus_search", "Search"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.session: SessionType | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="search-bar"):
            yield Input(placeholder="Search...", id="search-input")
            yield Button("Search", id="search-btn")
        with TabbedContent():
            with TabPane("Brands", id="brands-tab"):
                yield DataTable(id="brands-table")
            with TabPane("Products", id="products-tab"):
                yield DataTable(id="products-table")
            with TabPane("Vendors", id="vendors-tab"):
                yield DataTable(id="vendors-table")
            with TabPane("Quotes", id="quotes-tab"):
                yield DataTable(id="quotes-table")
            with TabPane("Forex", id="forex-tab"):
                yield DataTable(id="forex-table")
        yield Footer()

    def on_mount(self) -> None:
        self.session = Session()
        self._setup_tables()
        self._refresh_all()

    def _setup_tables(self) -> None:
        """Setup column headers for all tables."""
        brands_table = self.query_one("#brands-table", DataTable)
        brands_table.add_columns("ID", "Name", "Products")
        brands_table.cursor_type = "row"

        products_table = self.query_one("#products-table", DataTable)
        products_table.add_columns("ID", "Name", "Brand")
        products_table.cursor_type = "row"

        vendors_table = self.query_one("#vendors-table", DataTable)
        vendors_table.add_columns("ID", "Name", "Currency", "Discount", "Quotes")
        vendors_table.cursor_type = "row"

        quotes_table = self.query_one("#quotes-table", DataTable)
        quotes_table.add_columns("ID", "Vendor", "Product", "Price", "Currency")
        quotes_table.cursor_type = "row"

        forex_table = self.query_one("#forex-table", DataTable)
        forex_table.add_columns("ID", "Code", "USD/Unit", "Date")
        forex_table.cursor_type = "row"

    def _refresh_all(self, filter_by: str | None = None) -> None:
        """Refresh all data tables."""
        self._refresh_brands(filter_by)
        self._refresh_products(filter_by)
        self._refresh_vendors(filter_by)
        self._refresh_quotes(filter_by)
        self._refresh_forex(filter_by)

    def _refresh_brands(self, filter_by: str | None = None) -> None:
        table = self.query_one("#brands-table", DataTable)
        table.clear()
        results = BrandService.get_all(self.session, filter_by=filter_by)
        for b in results:
            products = ", ".join([p.name for p in b.products])
            table.add_row(b.id, b.name, products, key=str(b.id))

    def _refresh_products(self, filter_by: str | None = None) -> None:
        table = self.query_one("#products-table", DataTable)
        table.clear()
        results = ProductService.get_all(self.session, filter_by=filter_by)
        for p in results:
            table.add_row(p.id, p.name, p.brand.name, key=str(p.id))

    def _refresh_vendors(self, filter_by: str | None = None) -> None:
        table = self.query_one("#vendors-table", DataTable)
        table.clear()
        results = VendorService.get_all(self.session, filter_by=filter_by)
        for v in results:
            discount = f"{v.discount}%" if v.discount else "-"
            table.add_row(v.id, v.name, v.currency, discount, len(v.quotes), key=str(v.id))

    def _refresh_quotes(self, filter_by: str | None = None) -> None:
        table = self.query_one("#quotes-table", DataTable)
        table.clear()
        results = QuoteService.get_all(self.session, filter_by=filter_by)
        for q in results:
            product_name = f"{q.product.brand.name} {q.product.name}"
            table.add_row(q.id, q.vendor.name, product_name, f"{q.value:.2f}", q.currency, key=str(q.id))

    def _refresh_forex(self, filter_by: str | None = None) -> None:
        table = self.query_one("#forex-table", DataTable)
        table.clear()
        query = select(Forex).order_by(Forex.date.desc())
        if filter_by:
            query = query.where(Forex.code.ilike(f"%{filter_by}%"))
        results = self.session.execute(query).scalars().all()
        for f in results:
            table.add_row(f.id, f.code, f.usd_per_unit, str(f.date), key=str(f.id))

    def _get_active_tab(self) -> str:
        """Get the currently active tab ID."""
        tabbed = self.query_one(TabbedContent)
        return tabbed.active or "brands-tab"

    def action_add(self) -> None:
        """Add a new entity based on current tab."""
        active = self._get_active_tab()
        if active == "brands-tab":
            self.push_screen(AddBrandModal(), self._on_brand_added)
        elif active == "products-tab":
            self.push_screen(AddProductModal(), self._on_product_added)
        elif active == "vendors-tab":
            self.push_screen(AddVendorModal(), self._on_vendor_added)
        elif active == "quotes-tab":
            self.push_screen(AddQuoteModal(), self._on_quote_added)
        elif active == "forex-tab":
            self.push_screen(AddForexModal(), self._on_forex_added)

    def _on_brand_added(self, result: str | None) -> None:
        if result:
            try:
                BrandService.create(self.session, result)
                self.notify(f"Added brand: {result}")
                self._refresh_brands()
            except DuplicateError:
                self.notify(f"Brand '{result}' already exists", severity="warning")
            except ValidationError as e:
                self.notify(str(e), severity="error")

    def _on_product_added(self, result: tuple[str, str] | None) -> None:
        if result:
            brand_name, product_name = result
            try:
                brand = Brand.by_name(self.session, brand_name)
                if not brand:
                    brand = BrandService.create(self.session, brand_name)
                    self.notify(f"Created brand: {brand_name}")

                existing = Product.by_name(self.session, product_name)
                if existing:
                    self.notify(f"Product '{product_name}' already exists", severity="warning")
                    return

                product = Product(name=product_name, brand=brand)
                self.session.add(product)
                self.session.commit()
                self.notify(f"Added product: {product_name}")
                self._refresh_products()
                self._refresh_brands()
            except Exception as e:
                self.session.rollback()
                self.notify(str(e), severity="error")

    def _on_vendor_added(self, result: tuple[str, str, str, float] | None) -> None:
        if result:
            name, currency, discount_code, discount = result
            try:
                existing = Vendor.by_name(self.session, name)
                if existing:
                    self.notify(f"Vendor '{name}' already exists", severity="warning")
                    return

                vendor = Vendor(
                    name=name,
                    currency=currency,
                    discount_code=discount_code,
                    discount=discount,
                )
                self.session.add(vendor)
                self.session.commit()
                self.notify(f"Added vendor: {name}")
                self._refresh_vendors()
            except Exception as e:
                self.session.rollback()
                self.notify(str(e), severity="error")

    def _on_quote_added(self, result: tuple[str, str, str, float] | None) -> None:
        if result:
            vendor_name, product_name, brand_name, price = result
            try:
                vendor = Vendor.by_name(self.session, vendor_name)
                if not vendor:
                    self.notify(f"Vendor '{vendor_name}' not found", severity="error")
                    return

                product = Product.by_name(self.session, product_name)
                if not product:
                    if not brand_name:
                        self.notify("Product not found. Provide brand name for new product.", severity="error")
                        return
                    brand = Brand.by_name(self.session, brand_name)
                    if not brand:
                        brand = BrandService.create(self.session, brand_name)
                    product = Product(name=product_name, brand=brand)
                    self.session.add(product)
                    self.session.commit()

                value = price
                original_value = None
                original_currency = None

                if vendor.currency != "USD":
                    fx_rate = self.session.execute(
                        select(Forex).where(Forex.code == vendor.currency)
                    ).scalar_one_or_none()
                    if not fx_rate:
                        self.notify(f"Forex rate for '{vendor.currency}' not found", severity="error")
                        return
                    original_value = value
                    original_currency = vendor.currency
                    value = value * fx_rate.usd_per_unit

                quote = Quote(
                    vendor=vendor,
                    product=product,
                    currency="USD",
                    value=value,
                    original_value=original_value,
                    original_currency=original_currency,
                )
                self.session.add(quote)
                self.session.commit()
                self.notify(f"Added quote: {vendor_name} -> {product_name} = {price}")
                self._refresh_quotes()
            except Exception as e:
                self.session.rollback()
                self.notify(str(e), severity="error")

    def _on_forex_added(self, result: tuple[str, float, str | None] | None) -> None:
        if result:
            import datetime

            code, rate, date_str = result
            try:
                if date_str:
                    date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                else:
                    date = datetime.date.today()

                existing = self.session.execute(
                    select(Forex).where(Forex.code == code, Forex.date == date)
                ).scalar_one_or_none()
                if existing:
                    self.notify(f"Forex rate for '{code}' on {date} already exists", severity="warning")
                    return

                fx = Forex(code=code, usd_per_unit=rate, date=date)
                self.session.add(fx)
                self.session.commit()
                self.notify(f"Added forex rate: {code} = {rate}")
                self._refresh_forex()
            except ValueError:
                self.notify("Invalid date format. Use YYYY-MM-DD", severity="error")
            except Exception as e:
                self.session.rollback()
                self.notify(str(e), severity="error")

    def action_delete(self) -> None:
        """Delete the selected entity."""
        active = self._get_active_tab()
        table_id = active.replace("-tab", "-table")
        table = self.query_one(f"#{table_id}", DataTable)

        if table.cursor_row is None or table.row_count == 0:
            self.notify("No row selected", severity="warning")
            return

        row_key = table.get_row_at(table.cursor_row)
        entity_id = row_key[0]
        entity_name = row_key[1]

        entity_type = active.replace("-tab", "").rstrip("s")
        self.push_screen(
            ConfirmDeleteModal(entity_type, str(entity_name)),
            lambda confirmed: self._on_delete_confirmed(confirmed, entity_type, entity_id),
        )

    def _on_delete_confirmed(self, confirmed: bool, entity_type: str, entity_id: int) -> None:
        if not confirmed:
            return

        try:
            if entity_type == "brand":
                entity = self.session.get(Brand, entity_id)
            elif entity_type == "product":
                entity = self.session.get(Product, entity_id)
            elif entity_type == "vendor":
                entity = self.session.get(Vendor, entity_id)
            elif entity_type == "quote":
                entity = self.session.get(Quote, entity_id)
            elif entity_type == "forex":
                entity = self.session.get(Forex, entity_id)
            else:
                return

            if entity:
                self.session.delete(entity)
                self.session.commit()
                self.notify(f"Deleted {entity_type}")
                self._refresh_all()
        except Exception as e:
            self.session.rollback()
            self.notify(str(e), severity="error")

    def action_refresh(self) -> None:
        """Refresh all tables."""
        self._refresh_all()
        self.notify("Refreshed")

    def action_search(self) -> None:
        """Perform search with current input value."""
        search_input = self.query_one("#search-input", Input)
        query = search_input.value.strip() or None
        self._refresh_all(filter_by=query)
        if query:
            self.notify(f"Filtered by: {query}")
        else:
            self.notify("Filter cleared")

    def action_focus_search(self) -> None:
        """Focus the search input."""
        self.query_one("#search-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "search-btn":
            self.action_search()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search-input":
            self.action_search()

    def on_unmount(self) -> None:
        if self.session:
            self.session.close()


def main() -> None:
    """Entry point for TUI."""
    app = BuyerApp()
    app.run()


if __name__ == "__main__":
    main()
