#!/usr/bin/env python3
"""
Business logic service layer for buyer application.

This module contains service classes that handle business logic,
keeping it separate from models (data) and views (presentation).
"""

import datetime
import logging
from typing import Optional, List, Dict, Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .models import Brand, Product, Vendor, Quote, Forex, QuoteHistory, PriceAlert
from .audit import AuditService, AuditAction

logger = logging.getLogger("buyer")


class ServiceError(Exception):
    """Base exception for service layer errors"""

    pass


class ValidationError(ServiceError):
    """Raised when input validation fails"""

    pass


class DuplicateError(ServiceError):
    """Raised when attempting to create a duplicate entity"""

    pass


class NotFoundError(ServiceError):
    """Raised when an entity is not found"""

    pass


class BrandService:
    """Service for brand-related business logic"""

    @staticmethod
    def create(session: Session, name: str) -> Brand:
        """
        Create a new brand.

        Args:
            session: Database session
            name: Brand name

        Returns:
            Created Brand instance

        Raises:
            ValidationError: If name is invalid
            DuplicateError: If brand already exists
        """
        # Validate input
        name = name.strip()
        if not name:
            raise ValidationError("Brand name cannot be empty")
        if len(name) > 255:
            raise ValidationError("Brand name too long (max 255 characters)")

        # Check for duplicate
        existing = Brand.by_name(session, name)
        if existing:
            raise DuplicateError(f"Brand '{name}' already exists")

        # Create brand
        try:
            brand = Brand(name=name)
            session.add(brand)
            session.commit()
            logger.info(f"Created brand: {name}")

            # Audit log
            AuditService.log_create(
                entity_type="brand",
                entity_id=brand.id,
                entity_name=brand.name,
                session=session,
            )

            return brand
        except IntegrityError as e:
            session.rollback()
            logger.error(f"Failed to create brand '{name}': {e}")
            raise DuplicateError(f"Brand '{name}' already exists") from e
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error creating brand '{name}': {e}")
            raise ServiceError(f"Failed to create brand: {e}") from e

    @staticmethod
    def get_by_name(session: Session, name: str) -> Optional[Brand]:
        """
        Get a brand by name.

        Args:
            session: Database session
            name: Brand name

        Returns:
            Brand instance or None if not found
        """
        return Brand.by_name(session, name)

    @staticmethod
    def get_all(
        session: Session, filter_by: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Brand]:
        """
        Get all brands with optional filtering and pagination.

        Args:
            session: Database session
            filter_by: Optional name filter (case-insensitive partial match)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of Brand instances
        """
        query = select(Brand).options(joinedload(Brand.products))

        if filter_by:
            query = query.where(Brand.name.ilike(f"%{filter_by}%"))

        query = query.limit(limit).offset(offset)
        results = session.execute(query).unique().scalars().all()
        return list(results)

    @staticmethod
    def update(session: Session, name: str, new_name: str) -> Brand:
        """
        Update a brand's name.

        Args:
            session: Database session
            name: Current brand name
            new_name: New brand name

        Returns:
            Updated Brand instance

        Raises:
            NotFoundError: If brand not found
            ValidationError: If new name is invalid
            DuplicateError: If new name already exists
        """
        # Validate new name
        new_name = new_name.strip()
        if not new_name:
            raise ValidationError("Brand name cannot be empty")
        if len(new_name) > 255:
            raise ValidationError("Brand name too long (max 255 characters)")

        # Find brand
        brand = Brand.by_name(session, name)
        if not brand:
            raise NotFoundError(f"Brand '{name}' not found")

        # Check if new name is already taken
        if new_name != name:
            existing = Brand.by_name(session, new_name)
            if existing:
                raise DuplicateError(f"Brand '{new_name}' already exists")

        # Update
        try:
            brand.name = new_name
            session.commit()
            logger.info(f"Updated brand '{name}' to '{new_name}'")
            return brand
        except IntegrityError as e:
            session.rollback()
            logger.error(f"Failed to update brand '{name}': {e}")
            raise DuplicateError(f"Brand '{new_name}' already exists") from e
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error updating brand '{name}': {e}")
            raise ServiceError(f"Failed to update brand: {e}") from e

    @staticmethod
    def delete(session: Session, name: str) -> None:
        """
        Delete a brand.

        Args:
            session: Database session
            name: Brand name

        Raises:
            NotFoundError: If brand not found
        """
        brand = Brand.by_name(session, name)
        if not brand:
            raise NotFoundError(f"Brand '{name}' not found")

        try:
            session.delete(brand)
            session.commit()
            logger.info(f"Deleted brand: {name}")
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to delete brand '{name}': {e}")
            raise ServiceError(f"Failed to delete brand: {e}") from e


class ProductService:
    """Service for product-related business logic"""

    @staticmethod
    def create(session: Session, name: str, brand_name: str) -> Product:
        """
        Create a new product under a brand.

        Args:
            session: Database session
            name: Product name
            brand_name: Brand name (will be created if doesn't exist)

        Returns:
            Created Product instance

        Raises:
            ValidationError: If input is invalid
            DuplicateError: If product already exists
        """
        # Validate input
        name = name.strip()
        brand_name = brand_name.strip()

        if not name:
            raise ValidationError("Product name cannot be empty")
        if len(name) > 255:
            raise ValidationError("Product name too long (max 255 characters)")
        if not brand_name:
            raise ValidationError("Brand name cannot be empty")

        # Get or create brand
        brand = Brand.by_name(session, brand_name)
        if not brand:
            brand = BrandService.create(session, brand_name)

        # Check for duplicate product
        existing = Product.by_name(session, name)
        if existing:
            raise DuplicateError(f"Product '{name}' already exists")

        # Create product
        try:
            product = Product(name=name, brand=brand)
            session.add(product)
            session.commit()
            logger.info(f"Created product: {name} under brand: {brand_name}")
            return product
        except IntegrityError as e:
            session.rollback()
            logger.error(f"Failed to create product '{name}': {e}")
            raise DuplicateError(f"Product '{name}' already exists") from e
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error creating product '{name}': {e}")
            raise ServiceError(f"Failed to create product: {e}") from e

    @staticmethod
    def get_by_name(session: Session, name: str) -> Optional[Product]:
        """Get a product by name."""
        return Product.by_name(session, name)

    @staticmethod
    def get_all(
        session: Session, filter_by: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Product]:
        """
        Get all products with optional filtering and pagination.

        Args:
            session: Database session
            filter_by: Optional name filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of Product instances with brands eagerly loaded
        """
        query = select(Product).options(joinedload(Product.brand))

        if filter_by:
            query = query.where(Product.name.ilike(f"%{filter_by}%"))

        query = query.limit(limit).offset(offset)
        results = session.execute(query).unique().scalars().all()
        return list(results)


class VendorService:
    """Service for vendor-related business logic"""

    @staticmethod
    def create(
        session: Session,
        name: str,
        currency: str = "USD",
        discount_code: Optional[str] = None,
        discount: float = 0.0,
    ) -> Vendor:
        """
        Create a new vendor.

        Args:
            session: Database session
            name: Vendor name
            currency: Currency code (default: USD)
            discount_code: Optional discount code
            discount: Discount percentage (default: 0.0)

        Returns:
            Created Vendor instance

        Raises:
            ValidationError: If input is invalid
            DuplicateError: If vendor already exists
        """
        # Validate input
        name = name.strip()
        currency = currency.strip().upper()

        if not name:
            raise ValidationError("Vendor name cannot be empty")
        if len(name) > 255:
            raise ValidationError("Vendor name too long (max 255 characters)")
        if len(currency) != 3:
            raise ValidationError("Currency code must be 3 characters (ISO 4217)")
        if not (0 <= discount <= 100):
            raise ValidationError("Discount must be between 0 and 100")

        # Check for duplicate
        existing = Vendor.by_name(session, name)
        if existing:
            raise DuplicateError(f"Vendor '{name}' already exists")

        # Create vendor
        try:
            vendor = Vendor(
                name=name, currency=currency, discount_code=discount_code, discount=discount
            )
            session.add(vendor)
            session.commit()
            logger.info(f"Created vendor: {name} (currency: {currency})")
            return vendor
        except IntegrityError as e:
            session.rollback()
            logger.error(f"Failed to create vendor '{name}': {e}")
            raise DuplicateError(f"Vendor '{name}' already exists") from e
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error creating vendor '{name}': {e}")
            raise ServiceError(f"Failed to create vendor: {e}") from e

    @staticmethod
    def get_all(
        session: Session, filter_by: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Vendor]:
        """Get all vendors with pagination and eager loading."""
        query = select(Vendor).options(joinedload(Vendor.quotes))

        if filter_by:
            query = query.where(Vendor.name.ilike(f"%{filter_by}%"))

        query = query.limit(limit).offset(offset)
        results = session.execute(query).unique().scalars().all()
        return list(results)


class QuoteService:
    """Service for quote-related business logic"""

    @staticmethod
    def create(
        session: Session,
        vendor_name: str,
        product_name: str,
        price: float,
        brand_name: Optional[str] = None,
    ) -> Quote:
        """
        Create a new quote from a vendor for a product.

        Args:
            session: Database session
            vendor_name: Vendor name
            product_name: Product name
            price: Price in vendor's currency
            brand_name: Optional brand name (for creating new products)

        Returns:
            Created Quote instance

        Raises:
            ValidationError: If input is invalid
            NotFoundError: If vendor or product not found
        """
        # Validate input
        if price < 0:
            raise ValidationError("Price cannot be negative")

        # Get vendor
        vendor = Vendor.by_name(session, vendor_name)
        if not vendor:
            raise NotFoundError(f"Vendor '{vendor_name}' not found")

        # Get or create product
        product = Product.by_name(session, product_name)
        if not product:
            if not brand_name:
                raise ValidationError(
                    f"Product '{product_name}' not found and no brand name provided"
                )
            product = ProductService.create(session, product_name, brand_name)

        # Convert currency if needed
        value = price
        original_value = None
        original_currency = None

        if vendor.currency != "USD":
            fx_rate = session.execute(
                select(Forex)
                .where(Forex.code == vendor.currency)
                .order_by(Forex.date.desc())
            ).scalar_one_or_none()

            if not fx_rate:
                raise ValidationError(
                    f"Forex rate for '{vendor.currency}' not found. "
                    "Please add it using the add-fx command."
                )

            original_value = price
            original_currency = vendor.currency
            value = price * fx_rate.usd_per_unit

        # Create quote
        try:
            quote = Quote(
                vendor=vendor,
                product=product,
                currency="USD",
                value=value,
                original_value=original_value,
                original_currency=original_currency,
            )
            session.add(quote)
            session.commit()
            logger.info(
                f"Created quote: {vendor_name} -> {product_name} = {price} {vendor.currency}"
            )
            return quote
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error creating quote: {e}")
            raise ServiceError(f"Failed to create quote: {e}") from e

    @staticmethod
    def get_all(
        session: Session, filter_by: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Quote]:
        """
        Get all quotes with pagination and eager loading.

        Eagerly loads vendor, product, and brand to avoid N+1 queries.
        """
        query = (
            select(Quote)
            .options(
                joinedload(Quote.vendor),
                joinedload(Quote.product).joinedload(Product.brand),
            )
        )

        if filter_by:
            query = query.join(Product).where(Product.name.ilike(f"%{filter_by}%"))

        query = query.limit(limit).offset(offset)
        results = session.execute(query).unique().scalars().all()
        return list(results)

    @staticmethod
    def get_best_prices_by_product(
        session: Session, product_ids: Optional[List[int]] = None
    ) -> Dict[int, Quote]:
        """
        Get the best (lowest) price quote for each product.

        Args:
            session: Database session
            product_ids: Optional list of product IDs to filter

        Returns:
            Dict mapping product_id to the Quote with lowest value
        """
        from sqlalchemy import func as sqlfunc

        # Subquery to get minimum price per product
        subquery = (
            select(Quote.product_id, sqlfunc.min(Quote.value).label("min_value"))
            .group_by(Quote.product_id)
        )

        if product_ids:
            subquery = subquery.where(Quote.product_id.in_(product_ids))

        subquery = subquery.subquery()

        # Main query to get the actual quotes
        query = (
            select(Quote)
            .options(
                joinedload(Quote.vendor),
                joinedload(Quote.product).joinedload(Product.brand),
            )
            .join(
                subquery,
                (Quote.product_id == subquery.c.product_id)
                & (Quote.value == subquery.c.min_value),
            )
        )

        results = session.execute(query).unique().scalars().all()

        # Build dict, handling ties by keeping first encountered
        best_prices: Dict[int, Quote] = {}
        for quote in results:
            if quote.product_id not in best_prices:
                best_prices[quote.product_id] = quote

        return best_prices

    @staticmethod
    def update_price(
        session: Session, quote_id: int, new_price: float
    ) -> Quote:
        """
        Update a quote's price and record the change in history.

        Args:
            session: Database session
            quote_id: Quote ID
            new_price: New price value

        Returns:
            Updated Quote instance

        Raises:
            ValidationError: If price is invalid
            NotFoundError: If quote not found
        """
        if new_price < 0:
            raise ValidationError("Price cannot be negative")

        quote = session.get(Quote, quote_id)
        if not quote:
            raise NotFoundError(f"Quote with ID {quote_id} not found")

        old_value = quote.value
        try:
            quote.value = new_price
            session.flush()

            # Record history
            history = QuoteHistory(
                quote_id=quote.id,
                old_value=old_value,
                new_value=new_price,
                change_type="update",
            )
            session.add(history)
            session.commit()

            # Check for triggered alerts
            from .services import PriceAlertService
            PriceAlertService.check_alerts(session, quote.product, new_price)

            logger.info(f"Updated quote {quote_id} price: {old_value} -> {new_price}")
            return quote
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to update quote price: {e}")
            raise ServiceError(f"Failed to update quote price: {e}") from e


class ForexService:
    """Service for forex rate management"""

    @staticmethod
    def create(
        session: Session,
        code: str,
        usd_per_unit: float,
        date: Optional[datetime.date] = None,
    ) -> Forex:
        """
        Create a new forex rate.

        Args:
            session: Database session
            code: Currency code (ISO 4217)
            usd_per_unit: USD value per unit of currency
            date: Date for rate (defaults to today)

        Returns:
            Created Forex instance

        Raises:
            ValidationError: If input is invalid
            DuplicateError: If rate already exists for code and date
        """
        # Validate input
        code = code.strip().upper()
        if len(code) != 3:
            raise ValidationError("Currency code must be 3 characters (ISO 4217)")
        if usd_per_unit <= 0:
            raise ValidationError("Exchange rate must be positive")

        # Default to today
        if date is None:
            date = datetime.date.today()

        # Check for duplicate
        existing = session.execute(
            select(Forex).where(Forex.code == code, Forex.date == date)
        ).scalar_one_or_none()

        if existing:
            raise DuplicateError(f"Forex rate for '{code}' on {date} already exists")

        # Create forex rate
        try:
            fx = Forex(code=code, usd_per_unit=usd_per_unit, date=date)
            session.add(fx)
            session.commit()
            logger.info(f"Created forex rate: {code} = {usd_per_unit} USD per unit on {date}")
            return fx
        except IntegrityError as e:
            session.rollback()
            logger.error(f"Failed to create forex rate '{code}': {e}")
            raise DuplicateError(f"Forex rate for '{code}' on {date} already exists") from e
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error creating forex rate '{code}': {e}")
            raise ServiceError(f"Failed to create forex rate: {e}") from e

    @staticmethod
    def get_latest(session: Session, code: str) -> Optional[Forex]:
        """
        Get the latest forex rate for a currency.

        Args:
            session: Database session
            code: Currency code

        Returns:
            Latest Forex instance or None if not found
        """
        return session.execute(
            select(Forex).where(Forex.code == code.upper()).order_by(Forex.date.desc()).limit(1)
        ).scalar_one_or_none()


class QuoteHistoryService:
    """Service for quote history tracking"""

    @staticmethod
    def record_change(
        session: Session,
        quote: Quote,
        old_value: Optional[float],
        new_value: float,
        change_type: str = "update",
    ) -> QuoteHistory:
        """
        Record a price change for a quote.

        Args:
            session: Database session
            quote: Quote instance
            old_value: Previous price (None for new quotes)
            new_value: New price
            change_type: "create" or "update"

        Returns:
            Created QuoteHistory instance
        """
        try:
            history = QuoteHistory(
                quote_id=quote.id,
                old_value=old_value,
                new_value=new_value,
                change_type=change_type,
            )
            session.add(history)
            session.commit()
            logger.info(f"Recorded price change for quote {quote.id}: {old_value} -> {new_value}")
            return history
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to record price history: {e}")
            raise ServiceError(f"Failed to record price history: {e}") from e

    @staticmethod
    def get_history(session: Session, quote_id: int) -> List[QuoteHistory]:
        """
        Get price history for a specific quote.

        Args:
            session: Database session
            quote_id: Quote ID

        Returns:
            List of QuoteHistory entries ordered by changed_at descending, then id descending
        """
        results = session.execute(
            select(QuoteHistory)
            .where(QuoteHistory.quote_id == quote_id)
            .order_by(QuoteHistory.changed_at.desc(), QuoteHistory.id.desc())
        ).scalars().all()
        return list(results)

    @staticmethod
    def get_product_history(session: Session, product_id: int) -> List[QuoteHistory]:
        """
        Get all price changes for a product across all vendors.

        Args:
            session: Database session
            product_id: Product ID

        Returns:
            List of QuoteHistory entries ordered by changed_at descending, then id descending
        """
        results = session.execute(
            select(QuoteHistory)
            .join(Quote)
            .where(Quote.product_id == product_id)
            .order_by(QuoteHistory.changed_at.desc(), QuoteHistory.id.desc())
        ).scalars().all()
        return list(results)

    @staticmethod
    def compute_trend(history: List[QuoteHistory]) -> str:
        """
        Compute price trend from history.

        Args:
            history: List of QuoteHistory entries (newest first)

        Returns:
            "up", "down", "stable", or "new"
        """
        if not history:
            return "new"

        if len(history) < 2:
            if history[0].change_type == "create":
                return "new"
            return "stable"

        latest = history[0].new_value
        previous = history[1].new_value

        if latest > previous:
            return "up"
        elif latest < previous:
            return "down"
        else:
            return "stable"


class PriceAlertService:
    """Service for price alert management"""

    @staticmethod
    def create(
        session: Session,
        product_name: str,
        threshold_value: float,
        threshold_currency: str = "USD",
    ) -> PriceAlert:
        """
        Create a new price alert.

        Args:
            session: Database session
            product_name: Product name
            threshold_value: Price threshold
            threshold_currency: Currency for threshold (default: USD)

        Returns:
            Created PriceAlert instance

        Raises:
            ValidationError: If threshold is invalid
            NotFoundError: If product not found
        """
        if threshold_value <= 0:
            raise ValidationError("Threshold value must be positive")

        product = Product.by_name(session, product_name)
        if not product:
            raise NotFoundError(f"Product '{product_name}' not found")

        try:
            alert = PriceAlert(
                product_id=product.id,
                threshold_value=threshold_value,
                threshold_currency=threshold_currency.upper(),
            )
            session.add(alert)
            session.commit()
            logger.info(f"Created price alert for {product_name} at {threshold_value} {threshold_currency}")
            return alert
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to create price alert: {e}")
            raise ServiceError(f"Failed to create price alert: {e}") from e

    @staticmethod
    def check_alerts(session: Session, product: Product, current_price: float) -> List[PriceAlert]:
        """
        Check and trigger alerts for a product at current price.

        Args:
            session: Database session
            product: Product instance
            current_price: Current price in USD

        Returns:
            List of newly triggered alerts
        """
        import datetime

        alerts = session.execute(
            select(PriceAlert)
            .where(PriceAlert.product_id == product.id)
            .where(PriceAlert.active == 1)
            .where(PriceAlert.triggered_at.is_(None))
        ).scalars().all()

        triggered = []
        for alert in alerts:
            if current_price <= alert.threshold_value:
                alert.triggered_at = datetime.datetime.now()
                triggered.append(alert)
                logger.info(
                    f"Alert triggered for product {product.name}: "
                    f"price {current_price} <= threshold {alert.threshold_value}"
                )

        if triggered:
            session.commit()

        return triggered

    @staticmethod
    def get_active(session: Session) -> List[PriceAlert]:
        """
        Get all active alerts.

        Returns:
            List of active PriceAlert instances
        """
        results = session.execute(
            select(PriceAlert)
            .options(joinedload(PriceAlert.product))
            .where(PriceAlert.active == 1)
            .order_by(PriceAlert.created_at.desc())
        ).unique().scalars().all()
        return list(results)

    @staticmethod
    def get_triggered(session: Session) -> List[PriceAlert]:
        """
        Get all triggered alerts.

        Returns:
            List of triggered PriceAlert instances
        """
        results = session.execute(
            select(PriceAlert)
            .options(joinedload(PriceAlert.product))
            .where(PriceAlert.triggered_at.isnot(None))
            .order_by(PriceAlert.triggered_at.desc())
        ).unique().scalars().all()
        return list(results)

    @staticmethod
    def get_all(session: Session) -> List[PriceAlert]:
        """
        Get all alerts.

        Returns:
            List of all PriceAlert instances
        """
        results = session.execute(
            select(PriceAlert)
            .options(joinedload(PriceAlert.product))
            .order_by(PriceAlert.created_at.desc())
        ).unique().scalars().all()
        return list(results)

    @staticmethod
    def deactivate(session: Session, alert_id: int) -> PriceAlert:
        """
        Deactivate an alert.

        Args:
            session: Database session
            alert_id: Alert ID

        Returns:
            Updated PriceAlert instance

        Raises:
            NotFoundError: If alert not found
        """
        alert = session.get(PriceAlert, alert_id)
        if not alert:
            raise NotFoundError(f"Alert with ID {alert_id} not found")

        try:
            alert.active = 0
            session.commit()
            logger.info(f"Deactivated alert {alert_id}")
            return alert
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to deactivate alert: {e}")
            raise ServiceError(f"Failed to deactivate alert: {e}") from e
