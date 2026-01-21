#!/usr/bin/env python3
"""
Business logic service layer for buylog application.

This module contains service classes that handle business logic,
keeping it separate from models (data) and views (presentation).
"""

import csv
import datetime
import io
import json
import logging
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .models import (
    Brand,
    Product,
    Vendor,
    Quote,
    Forex,
    QuoteHistory,
    PriceAlert,
    PurchaseList,
    Note,
    Tag,
    EntityTag,
    Watchlist,
    QUOTE_STATUSES,
)
from .audit import AuditService

logger = logging.getLogger("buylog")


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
        session: Session,
        filter_by: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
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
        session: Session,
        filter_by: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
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
                name=name,
                currency=currency,
                discount_code=discount_code,
                discount=discount,
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
        session: Session,
        filter_by: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
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
        session: Session,
        filter_by: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Quote]:
        """
        Get all quotes with pagination and eager loading.

        Eagerly loads vendor, product, and brand to avoid N+1 queries.
        """
        query = select(Quote).options(
            joinedload(Quote.vendor),
            joinedload(Quote.product).joinedload(Product.brand),
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
        min_price_query = select(
            Quote.product_id, sqlfunc.min(Quote.value).label("min_value")
        ).group_by(Quote.product_id)

        if product_ids:
            min_price_query = min_price_query.where(Quote.product_id.in_(product_ids))

        min_price_subquery = min_price_query.subquery()

        # Main query to get the actual quotes
        query = (
            select(Quote)
            .options(
                joinedload(Quote.vendor),
                joinedload(Quote.product).joinedload(Product.brand),
            )
            .join(
                min_price_subquery,
                (Quote.product_id == min_price_subquery.c.product_id)
                & (Quote.value == min_price_subquery.c.min_value),
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
    def update_price(session: Session, quote_id: int, new_price: float) -> Quote:
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

    @staticmethod
    def set_status(session: Session, quote_id: int, status: str) -> Quote:
        """
        Set the status of a quote.

        Args:
            session: Database session
            quote_id: Quote ID
            status: Status value (considering, ordered, received)

        Returns:
            Updated Quote instance

        Raises:
            ValidationError: If status is invalid
            NotFoundError: If quote not found
        """
        status = status.lower()
        if status not in QUOTE_STATUSES:
            raise ValidationError(
                f"Invalid status '{status}'. Must be one of: {', '.join(QUOTE_STATUSES)}"
            )

        quote = session.get(Quote, quote_id)
        if not quote:
            raise NotFoundError(f"Quote with ID {quote_id} not found")

        try:
            quote.status = status
            session.commit()
            logger.info(f"Set status '{status}' for quote {quote_id}")
            return quote
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to set quote status: {e}")
            raise ServiceError(f"Failed to set quote status: {e}") from e

    @staticmethod
    def get_by_status(session: Session, status: str) -> List[Quote]:
        """
        Get all quotes with a specific status.

        Args:
            session: Database session
            status: Status to filter by

        Returns:
            List of Quote instances
        """
        status = status.lower()
        if status not in QUOTE_STATUSES:
            raise ValidationError(
                f"Invalid status '{status}'. Must be one of: {', '.join(QUOTE_STATUSES)}"
            )

        results = (
            session.execute(
                select(Quote)
                .options(
                    joinedload(Quote.vendor),
                    joinedload(Quote.product).joinedload(Product.brand),
                )
                .where(Quote.status == status)
                .order_by(Quote.created_at.desc())
            )
            .unique()
            .scalars()
            .all()
        )
        return list(results)


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
            logger.info(
                f"Created forex rate: {code} = {usd_per_unit} USD per unit on {date}"
            )
            return fx
        except IntegrityError as e:
            session.rollback()
            logger.error(f"Failed to create forex rate '{code}': {e}")
            raise DuplicateError(
                f"Forex rate for '{code}' on {date} already exists"
            ) from e
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
            select(Forex)
            .where(Forex.code == code.upper())
            .order_by(Forex.date.desc())
            .limit(1)
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
            logger.info(
                f"Recorded price change for quote {quote.id}: {old_value} -> {new_value}"
            )
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
        results = (
            session.execute(
                select(QuoteHistory)
                .where(QuoteHistory.quote_id == quote_id)
                .order_by(QuoteHistory.changed_at.desc(), QuoteHistory.id.desc())
            )
            .scalars()
            .all()
        )
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
        results = (
            session.execute(
                select(QuoteHistory)
                .join(Quote)
                .where(Quote.product_id == product_id)
                .order_by(QuoteHistory.changed_at.desc(), QuoteHistory.id.desc())
            )
            .scalars()
            .all()
        )
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
            logger.info(
                f"Created price alert for {product_name} at {threshold_value} {threshold_currency}"
            )
            return alert
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to create price alert: {e}")
            raise ServiceError(f"Failed to create price alert: {e}") from e

    @staticmethod
    def check_alerts(
        session: Session, product: Product, current_price: float
    ) -> List[PriceAlert]:
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

        alerts = (
            session.execute(
                select(PriceAlert)
                .where(PriceAlert.product_id == product.id)
                .where(PriceAlert.active == 1)
                .where(PriceAlert.triggered_at.is_(None))
            )
            .scalars()
            .all()
        )

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
        results = (
            session.execute(
                select(PriceAlert)
                .options(joinedload(PriceAlert.product))
                .where(PriceAlert.active == 1)
                .order_by(PriceAlert.created_at.desc())
            )
            .unique()
            .scalars()
            .all()
        )
        return list(results)

    @staticmethod
    def get_triggered(session: Session) -> List[PriceAlert]:
        """
        Get all triggered alerts.

        Returns:
            List of triggered PriceAlert instances
        """
        results = (
            session.execute(
                select(PriceAlert)
                .options(joinedload(PriceAlert.product))
                .where(PriceAlert.triggered_at.isnot(None))
                .order_by(PriceAlert.triggered_at.desc())
            )
            .unique()
            .scalars()
            .all()
        )
        return list(results)

    @staticmethod
    def get_all(session: Session) -> List[PriceAlert]:
        """
        Get all alerts.

        Returns:
            List of all PriceAlert instances
        """
        results = (
            session.execute(
                select(PriceAlert)
                .options(joinedload(PriceAlert.product))
                .order_by(PriceAlert.created_at.desc())
            )
            .unique()
            .scalars()
            .all()
        )
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


class ComparisonService:
    """Service for price comparison functionality"""

    @staticmethod
    def compare_product(session: Session, product_name: str) -> Dict[str, Any]:
        """
        Compare prices for a specific product across all vendors.

        Args:
            session: Database session
            product_name: Exact product name

        Returns:
            Dict with product info, quotes sorted by price, and statistics
        """
        product = Product.by_name(session, product_name)
        if not product:
            raise NotFoundError(f"Product '{product_name}' not found")

        quotes = (
            session.execute(
                select(Quote)
                .options(
                    joinedload(Quote.vendor),
                    joinedload(Quote.product).joinedload(Product.brand),
                )
                .where(Quote.product_id == product.id)
                .order_by(Quote.value.asc())
            )
            .unique()
            .scalars()
            .all()
        )

        if not quotes:
            return {
                "product": product,
                "quotes": [],
                "best_price": None,
                "worst_price": None,
                "avg_price": None,
                "price_spread": None,
                "savings": None,
            }

        prices = [q.value for q in quotes]
        best = min(prices)
        worst = max(prices)
        avg = sum(prices) / len(prices)

        return {
            "product": product,
            "quotes": list(quotes),
            "best_price": best,
            "worst_price": worst,
            "avg_price": avg,
            "price_spread": worst - best,
            "savings": worst - best,
            "num_vendors": len(quotes),
        }

    @staticmethod
    def compare_by_search(session: Session, search_term: str) -> Dict[str, Any]:
        """
        Compare prices for products matching a search term.

        Args:
            session: Database session
            search_term: Partial product name to search

        Returns:
            Dict with matching products and their comparison data
        """
        # Find matching products
        products = (
            session.execute(
                select(Product)
                .options(joinedload(Product.brand))
                .where(Product.name.ilike(f"%{search_term}%"))
                .order_by(Product.name)
            )
            .unique()
            .scalars()
            .all()
        )

        if not products:
            raise NotFoundError(f"No products found matching '{search_term}'")

        comparisons = []
        for product in products:
            comparison = ComparisonService.compare_product(session, product.name)
            if comparison["quotes"]:  # Only include products with quotes
                comparisons.append(comparison)

        # Sort by best price
        comparisons.sort(key=lambda c: c["best_price"] or float("inf"))

        return {
            "search_term": search_term,
            "products": comparisons,
            "total_products": len(comparisons),
        }

    @staticmethod
    def compare_by_category(session: Session, category: str) -> Dict[str, Any]:
        """
        Compare prices for all products in a category.

        Args:
            session: Database session
            category: Product category name

        Returns:
            Dict with products in category and their comparison data
        """
        products = (
            session.execute(
                select(Product)
                .options(joinedload(Product.brand))
                .where(Product.category.ilike(f"%{category}%"))
                .order_by(Product.name)
            )
            .unique()
            .scalars()
            .all()
        )

        if not products:
            raise NotFoundError(f"No products found in category '{category}'")

        comparisons = []
        for product in products:
            comparison = ComparisonService.compare_product(session, product.name)
            if comparison["quotes"]:
                comparisons.append(comparison)

        comparisons.sort(key=lambda c: c["best_price"] or float("inf"))

        return {
            "category": category,
            "products": comparisons,
            "total_products": len(comparisons),
        }

    @staticmethod
    def compare_by_brand(session: Session, brand_name: str) -> Dict[str, Any]:
        """
        Compare prices for all products from a brand.

        Args:
            session: Database session
            brand_name: Brand name

        Returns:
            Dict with products from brand and their comparison data
        """
        brand = Brand.by_name(session, brand_name)
        if not brand:
            raise NotFoundError(f"Brand '{brand_name}' not found")

        comparisons = []
        for product in brand.products:
            comparison = ComparisonService.compare_product(session, product.name)
            if comparison["quotes"]:
                comparisons.append(comparison)

        comparisons.sort(key=lambda c: c["best_price"] or float("inf"))

        return {
            "brand": brand,
            "products": comparisons,
            "total_products": len(comparisons),
        }

    @staticmethod
    def get_categories(session: Session) -> List[str]:
        """
        Get all unique product categories.

        Returns:
            List of category names
        """
        results = (
            session.execute(
                select(Product.category)
                .where(Product.category.isnot(None))
                .distinct()
                .order_by(Product.category)
            )
            .scalars()
            .all()
        )
        return [c for c in results if c]

    @staticmethod
    def set_product_category(
        session: Session, product_name: str, category: str
    ) -> Product:
        """
        Set or update a product's category.

        Args:
            session: Database session
            product_name: Product name
            category: Category to assign

        Returns:
            Updated Product instance
        """
        product = Product.by_name(session, product_name)
        if not product:
            raise NotFoundError(f"Product '{product_name}' not found")

        try:
            product.category = category
            session.commit()
            logger.info(f"Set category '{category}' for product '{product_name}'")
            return product
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to set product category: {e}")
            raise ServiceError(f"Failed to set product category: {e}") from e


class PurchaseListService:
    """Service for purchase list management"""

    @staticmethod
    def create(
        session: Session,
        name: str,
        description: Optional[str] = None,
    ) -> PurchaseList:
        """
        Create a new purchase list.

        Args:
            session: Database session
            name: List name
            description: Optional description

        Returns:
            Created PurchaseList instance
        """
        name = name.strip()
        if not name:
            raise ValidationError("Purchase list name cannot be empty")

        existing = PurchaseList.by_name(session, name)
        if existing:
            raise DuplicateError(f"Purchase list '{name}' already exists")

        try:
            purchase_list = PurchaseList(name=name, description=description)
            session.add(purchase_list)
            session.commit()
            logger.info(f"Created purchase list: {name}")
            return purchase_list
        except IntegrityError as e:
            session.rollback()
            raise DuplicateError(f"Purchase list '{name}' already exists") from e
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to create purchase list: {e}")
            raise ServiceError(f"Failed to create purchase list: {e}") from e

    @staticmethod
    def get_by_name(session: Session, name: str) -> Optional[PurchaseList]:
        """Get a purchase list by name."""
        return PurchaseList.by_name(session, name)

    @staticmethod
    def get_all(session: Session) -> List[PurchaseList]:
        """Get all purchase lists."""
        results = (
            session.execute(
                select(PurchaseList).order_by(PurchaseList.created_at.desc())
            )
            .scalars()
            .all()
        )
        return list(results)

    @staticmethod
    def add_quote(session: Session, list_name: str, quote_id: int) -> PurchaseList:
        """
        Add a quote to a purchase list.

        Args:
            session: Database session
            list_name: Purchase list name
            quote_id: Quote ID to add

        Returns:
            Updated PurchaseList instance
        """
        purchase_list = PurchaseList.by_name(session, list_name)
        if not purchase_list:
            raise NotFoundError(f"Purchase list '{list_name}' not found")

        quote = session.get(Quote, quote_id)
        if not quote:
            raise NotFoundError(f"Quote with ID {quote_id} not found")

        if quote in purchase_list.quotes:
            raise DuplicateError(f"Quote {quote_id} already in list '{list_name}'")

        try:
            purchase_list.quotes.append(quote)
            session.commit()
            logger.info(f"Added quote {quote_id} to list '{list_name}'")
            return purchase_list
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to add quote to list: {e}")
            raise ServiceError(f"Failed to add quote to list: {e}") from e

    @staticmethod
    def remove_quote(session: Session, list_name: str, quote_id: int) -> PurchaseList:
        """
        Remove a quote from a purchase list.

        Args:
            session: Database session
            list_name: Purchase list name
            quote_id: Quote ID to remove

        Returns:
            Updated PurchaseList instance
        """
        purchase_list = PurchaseList.by_name(session, list_name)
        if not purchase_list:
            raise NotFoundError(f"Purchase list '{list_name}' not found")

        quote = session.get(Quote, quote_id)
        if not quote:
            raise NotFoundError(f"Quote with ID {quote_id} not found")

        if quote not in purchase_list.quotes:
            raise NotFoundError(f"Quote {quote_id} not in list '{list_name}'")

        try:
            purchase_list.quotes.remove(quote)
            session.commit()
            logger.info(f"Removed quote {quote_id} from list '{list_name}'")
            return purchase_list
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to remove quote from list: {e}")
            raise ServiceError(f"Failed to remove quote from list: {e}") from e

    @staticmethod
    def delete(session: Session, name: str) -> None:
        """Delete a purchase list."""
        purchase_list = PurchaseList.by_name(session, name)
        if not purchase_list:
            raise NotFoundError(f"Purchase list '{name}' not found")

        try:
            session.delete(purchase_list)
            session.commit()
            logger.info(f"Deleted purchase list: {name}")
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to delete purchase list: {e}")
            raise ServiceError(f"Failed to delete purchase list: {e}") from e


class NoteService:
    """Service for notes management"""

    @staticmethod
    def create(
        session: Session,
        entity_type: str,
        entity_id: int,
        content: str,
    ) -> Note:
        """
        Create a note for an entity.

        Args:
            session: Database session
            entity_type: Type of entity ('product', 'vendor', 'quote', etc.)
            entity_id: ID of the entity
            content: Note content

        Returns:
            Created Note instance
        """
        content = content.strip()
        if not content:
            raise ValidationError("Note content cannot be empty")

        entity_type = entity_type.lower()
        valid_types = ["product", "vendor", "quote", "brand", "purchase_list"]
        if entity_type not in valid_types:
            raise ValidationError(
                f"Invalid entity type. Must be one of: {', '.join(valid_types)}"
            )

        try:
            note = Note(
                entity_type=entity_type,
                entity_id=entity_id,
                content=content,
            )
            session.add(note)
            session.commit()
            logger.info(f"Created note for {entity_type}:{entity_id}")
            return note
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to create note: {e}")
            raise ServiceError(f"Failed to create note: {e}") from e

    @staticmethod
    def get_for_entity(
        session: Session, entity_type: str, entity_id: int
    ) -> List[Note]:
        """
        Get all notes for an entity.

        Args:
            session: Database session
            entity_type: Type of entity
            entity_id: ID of the entity

        Returns:
            List of Note instances
        """
        results = (
            session.execute(
                select(Note)
                .where(Note.entity_type == entity_type.lower())
                .where(Note.entity_id == entity_id)
                .order_by(Note.created_at.desc())
            )
            .scalars()
            .all()
        )
        return list(results)

    @staticmethod
    def update(session: Session, note_id: int, content: str) -> Note:
        """
        Update a note's content.

        Args:
            session: Database session
            note_id: Note ID
            content: New content

        Returns:
            Updated Note instance
        """
        content = content.strip()
        if not content:
            raise ValidationError("Note content cannot be empty")

        note = session.get(Note, note_id)
        if not note:
            raise NotFoundError(f"Note with ID {note_id} not found")

        try:
            note.content = content
            note.updated_at = datetime.datetime.now()
            session.commit()
            logger.info(f"Updated note {note_id}")
            return note
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to update note: {e}")
            raise ServiceError(f"Failed to update note: {e}") from e

    @staticmethod
    def delete(session: Session, note_id: int) -> None:
        """Delete a note."""
        note = session.get(Note, note_id)
        if not note:
            raise NotFoundError(f"Note with ID {note_id} not found")

        try:
            session.delete(note)
            session.commit()
            logger.info(f"Deleted note {note_id}")
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to delete note: {e}")
            raise ServiceError(f"Failed to delete note: {e}") from e


class TagService:
    """Service for tag management"""

    @staticmethod
    def create(
        session: Session,
        name: str,
        color: Optional[str] = None,
    ) -> Tag:
        """
        Create a new tag.

        Args:
            session: Database session
            name: Tag name
            color: Optional hex color for UI

        Returns:
            Created Tag instance
        """
        name = name.strip().lower()
        if not name:
            raise ValidationError("Tag name cannot be empty")

        existing = Tag.by_name(session, name)
        if existing:
            raise DuplicateError(f"Tag '{name}' already exists")

        try:
            tag = Tag(name=name, color=color)
            session.add(tag)
            session.commit()
            logger.info(f"Created tag: {name}")
            return tag
        except IntegrityError as e:
            session.rollback()
            raise DuplicateError(f"Tag '{name}' already exists") from e
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to create tag: {e}")
            raise ServiceError(f"Failed to create tag: {e}") from e

    @staticmethod
    def get_all(session: Session) -> List[Tag]:
        """Get all tags."""
        results = session.execute(select(Tag).order_by(Tag.name)).scalars().all()
        return list(results)

    @staticmethod
    def add_to_entity(
        session: Session,
        tag_name: str,
        entity_type: str,
        entity_id: int,
    ) -> EntityTag:
        """
        Add a tag to an entity.

        Args:
            session: Database session
            tag_name: Tag name
            entity_type: Type of entity
            entity_id: ID of the entity

        Returns:
            Created EntityTag instance
        """
        tag = Tag.by_name(session, tag_name.lower())
        if not tag:
            # Auto-create tag if it doesn't exist
            tag = TagService.create(session, tag_name)

        entity_type = entity_type.lower()

        # Check if already tagged
        existing = session.execute(
            select(EntityTag)
            .where(EntityTag.tag_id == tag.id)
            .where(EntityTag.entity_type == entity_type)
            .where(EntityTag.entity_id == entity_id)
        ).scalar_one_or_none()

        if existing:
            raise DuplicateError(f"Entity already has tag '{tag_name}'")

        try:
            entity_tag = EntityTag(
                tag_id=tag.id,
                entity_type=entity_type,
                entity_id=entity_id,
            )
            session.add(entity_tag)
            session.commit()
            logger.info(f"Added tag '{tag_name}' to {entity_type}:{entity_id}")
            return entity_tag
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to add tag to entity: {e}")
            raise ServiceError(f"Failed to add tag to entity: {e}") from e

    @staticmethod
    def remove_from_entity(
        session: Session,
        tag_name: str,
        entity_type: str,
        entity_id: int,
    ) -> None:
        """
        Remove a tag from an entity.

        Args:
            session: Database session
            tag_name: Tag name
            entity_type: Type of entity
            entity_id: ID of the entity
        """
        tag = Tag.by_name(session, tag_name.lower())
        if not tag:
            raise NotFoundError(f"Tag '{tag_name}' not found")

        entity_type = entity_type.lower()

        entity_tag = session.execute(
            select(EntityTag)
            .where(EntityTag.tag_id == tag.id)
            .where(EntityTag.entity_type == entity_type)
            .where(EntityTag.entity_id == entity_id)
        ).scalar_one_or_none()

        if not entity_tag:
            raise NotFoundError(f"Entity does not have tag '{tag_name}'")

        try:
            session.delete(entity_tag)
            session.commit()
            logger.info(f"Removed tag '{tag_name}' from {entity_type}:{entity_id}")
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to remove tag from entity: {e}")
            raise ServiceError(f"Failed to remove tag from entity: {e}") from e

    @staticmethod
    def get_for_entity(session: Session, entity_type: str, entity_id: int) -> List[Tag]:
        """
        Get all tags for an entity.

        Args:
            session: Database session
            entity_type: Type of entity
            entity_id: ID of the entity

        Returns:
            List of Tag instances
        """
        results = (
            session.execute(
                select(Tag)
                .join(EntityTag)
                .where(EntityTag.entity_type == entity_type.lower())
                .where(EntityTag.entity_id == entity_id)
                .order_by(Tag.name)
            )
            .scalars()
            .all()
        )
        return list(results)

    @staticmethod
    def get_entities_by_tag(
        session: Session, tag_name: str, entity_type: Optional[str] = None
    ) -> List[EntityTag]:
        """
        Get all entities with a specific tag.

        Args:
            session: Database session
            tag_name: Tag name
            entity_type: Optional filter by entity type

        Returns:
            List of EntityTag instances
        """
        tag = Tag.by_name(session, tag_name.lower())
        if not tag:
            raise NotFoundError(f"Tag '{tag_name}' not found")

        query = (
            select(EntityTag)
            .options(joinedload(EntityTag.tag))
            .where(EntityTag.tag_id == tag.id)
        )

        if entity_type:
            query = query.where(EntityTag.entity_type == entity_type.lower())

        results = session.execute(query).unique().scalars().all()
        return list(results)


class WatchlistService:
    """Service for watchlist management"""

    @staticmethod
    def create(
        session: Session,
        product_name: str,
        target_price: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> Watchlist:
        """
        Add a product to the watchlist.

        Args:
            session: Database session
            product_name: Product name
            target_price: Optional target price
            notes: Optional notes

        Returns:
            Created Watchlist instance
        """
        product = Product.by_name(session, product_name)
        if not product:
            raise NotFoundError(f"Product '{product_name}' not found")

        # Check if already on watchlist (and active)
        existing = session.execute(
            select(Watchlist)
            .where(Watchlist.product_id == product.id)
            .where(Watchlist.active == 1)
        ).scalar_one_or_none()

        if existing:
            raise DuplicateError(f"Product '{product_name}' already on watchlist")

        try:
            watchlist = Watchlist(
                product_id=product.id,
                target_price=target_price,
                notes=notes,
            )
            session.add(watchlist)
            session.commit()
            logger.info(f"Added '{product_name}' to watchlist")
            return watchlist
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to add to watchlist: {e}")
            raise ServiceError(f"Failed to add to watchlist: {e}") from e

    @staticmethod
    def get_all(session: Session) -> List[Watchlist]:
        """Get all watchlist entries."""
        results = (
            session.execute(
                select(Watchlist)
                .options(joinedload(Watchlist.product).joinedload(Product.brand))
                .order_by(Watchlist.created_at.desc())
            )
            .unique()
            .scalars()
            .all()
        )
        return list(results)

    @staticmethod
    def get_active(session: Session) -> List[Watchlist]:
        """Get all active watchlist entries."""
        results = (
            session.execute(
                select(Watchlist)
                .options(joinedload(Watchlist.product).joinedload(Product.brand))
                .where(Watchlist.active == 1)
                .order_by(Watchlist.created_at.desc())
            )
            .unique()
            .scalars()
            .all()
        )
        return list(results)

    @staticmethod
    def update(
        session: Session,
        watchlist_id: int,
        target_price: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> Watchlist:
        """
        Update a watchlist entry.

        Args:
            session: Database session
            watchlist_id: Watchlist ID
            target_price: New target price (None to keep existing)
            notes: New notes (None to keep existing)

        Returns:
            Updated Watchlist instance
        """
        watchlist = session.get(Watchlist, watchlist_id)
        if not watchlist:
            raise NotFoundError(f"Watchlist entry {watchlist_id} not found")

        try:
            if target_price is not None:
                watchlist.target_price = target_price
            if notes is not None:
                watchlist.notes = notes
            session.commit()
            logger.info(f"Updated watchlist entry {watchlist_id}")
            return watchlist
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to update watchlist: {e}")
            raise ServiceError(f"Failed to update watchlist: {e}") from e

    @staticmethod
    def deactivate(session: Session, watchlist_id: int) -> Watchlist:
        """
        Deactivate a watchlist entry.

        Args:
            session: Database session
            watchlist_id: Watchlist ID

        Returns:
            Updated Watchlist instance
        """
        watchlist = session.get(Watchlist, watchlist_id)
        if not watchlist:
            raise NotFoundError(f"Watchlist entry {watchlist_id} not found")

        try:
            watchlist.active = 0
            session.commit()
            logger.info(f"Deactivated watchlist entry {watchlist_id}")
            return watchlist
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to deactivate watchlist: {e}")
            raise ServiceError(f"Failed to deactivate watchlist: {e}") from e

    @staticmethod
    def delete(session: Session, watchlist_id: int) -> None:
        """Delete a watchlist entry."""
        watchlist = session.get(Watchlist, watchlist_id)
        if not watchlist:
            raise NotFoundError(f"Watchlist entry {watchlist_id} not found")

        try:
            session.delete(watchlist)
            session.commit()
            logger.info(f"Deleted watchlist entry {watchlist_id}")
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to delete watchlist: {e}")
            raise ServiceError(f"Failed to delete watchlist: {e}") from e


class ImportService:
    """Service for importing data from CSV/JSON files."""

    @staticmethod
    def import_quotes_csv(
        session: Session,
        file_path: str | Path,
        create_missing: bool = True,
    ) -> Dict[str, Any]:
        """
        Import quotes from a CSV file.

        Expected CSV columns: vendor, product, brand, price, currency, shipping, tax_rate

        Args:
            session: Database session
            file_path: Path to CSV file
            create_missing: If True, create missing vendors/products/brands

        Returns:
            Dict with import statistics
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise NotFoundError(f"File not found: {file_path}")

        imported = 0
        skipped = 0
        errors: list[str] = []
        created_vendors: list[str] = []
        created_products: list[str] = []

        try:
            with open(file_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row_num, row in enumerate(reader, start=2):
                    try:
                        result = ImportService._import_quote_row(
                            session, row, create_missing
                        )
                        if result["imported"]:
                            imported += 1
                            if result.get("created_vendor"):
                                created_vendors.append(str(result["created_vendor"]))
                            if result.get("created_product"):
                                created_products.append(str(result["created_product"]))
                        else:
                            skipped += 1
                    except Exception as e:
                        errors.append(f"Row {row_num}: {e}")
                        skipped += 1

            logger.info(f"Imported {imported} quotes from {file_path}")
            return {
                "imported": imported,
                "skipped": skipped,
                "errors": errors,
                "created_vendors": created_vendors,
                "created_products": created_products,
            }
        except Exception as e:
            logger.error(f"Failed to import CSV: {e}")
            raise ServiceError(f"Failed to import CSV: {e}") from e

    @staticmethod
    def _import_quote_row(
        session: Session, row: Dict[str, str], create_missing: bool
    ) -> Dict[str, Any]:
        """Import a single quote row."""
        result: Dict[str, Any] = {"imported": False}

        vendor_name = row.get("vendor", "").strip()
        product_name = row.get("product", "").strip()
        brand_name = row.get("brand", "").strip()
        price_str = row.get("price", "").strip()
        currency = row.get("currency", "USD").strip().upper() or "USD"
        shipping_str = row.get("shipping", "").strip()
        tax_rate_str = row.get("tax_rate", "").strip()

        if not vendor_name or not product_name or not price_str:
            raise ValidationError("Missing required fields: vendor, product, price")

        try:
            price = float(price_str)
        except ValueError:
            raise ValidationError(f"Invalid price: {price_str}")

        shipping = float(shipping_str) if shipping_str else None
        tax_rate = float(tax_rate_str) if tax_rate_str else None

        # Get or create vendor
        vendor = Vendor.by_name(session, vendor_name)
        if not vendor:
            if create_missing:
                vendor = Vendor(name=vendor_name, currency=currency)
                session.add(vendor)
                session.flush()
                result["created_vendor"] = vendor_name
            else:
                raise NotFoundError(f"Vendor not found: {vendor_name}")

        # Get or create product
        product = Product.by_name(session, product_name)
        if not product:
            if create_missing:
                if not brand_name:
                    raise ValidationError(
                        f"Brand required for new product: {product_name}"
                    )
                brand = Brand.by_name(session, brand_name)
                if not brand:
                    brand = Brand(name=brand_name)
                    session.add(brand)
                    session.flush()
                product = Product(name=product_name, brand=brand)
                session.add(product)
                session.flush()
                result["created_product"] = product_name
            else:
                raise NotFoundError(f"Product not found: {product_name}")

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

            if fx_rate:
                original_value = price
                original_currency = vendor.currency
                value = price * fx_rate.usd_per_unit

        # Create quote
        quote = Quote(
            vendor=vendor,
            product=product,
            currency="USD",
            value=value,
            original_value=original_value,
            original_currency=original_currency,
            shipping_cost=shipping,
            tax_rate=tax_rate,
        )
        session.add(quote)
        session.commit()
        result["imported"] = True
        return result

    @staticmethod
    def import_quotes_json(
        session: Session,
        file_path: str | Path,
        create_missing: bool = True,
    ) -> Dict[str, Any]:
        """
        Import quotes from a JSON file.

        Expected JSON structure: [{"vendor": "...", "product": "...", "brand": "...", "price": 100, ...}, ...]

        Args:
            session: Database session
            file_path: Path to JSON file
            create_missing: If True, create missing vendors/products/brands

        Returns:
            Dict with import statistics
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise NotFoundError(f"File not found: {file_path}")

        imported = 0
        skipped = 0
        errors: list[str] = []
        created_vendors: list[str] = []
        created_products: list[str] = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                raise ValidationError("JSON must be an array of quote objects")

            for idx, item in enumerate(data):
                try:
                    # Convert JSON item to row dict
                    row = {
                        "vendor": str(item.get("vendor", "")),
                        "product": str(item.get("product", "")),
                        "brand": str(item.get("brand", "")),
                        "price": str(item.get("price", "")),
                        "currency": str(item.get("currency", "USD")),
                        "shipping": str(item.get("shipping", "")),
                        "tax_rate": str(item.get("tax_rate", "")),
                    }
                    result = ImportService._import_quote_row(
                        session, row, create_missing
                    )
                    if result["imported"]:
                        imported += 1
                        if result.get("created_vendor"):
                            created_vendors.append(str(result["created_vendor"]))
                        if result.get("created_product"):
                            created_products.append(str(result["created_product"]))
                    else:
                        skipped += 1
                except Exception as e:
                    errors.append(f"Item {idx}: {e}")
                    skipped += 1

            logger.info(f"Imported {imported} quotes from {file_path}")
            return {
                "imported": imported,
                "skipped": skipped,
                "errors": errors,
                "created_vendors": created_vendors,
                "created_products": created_products,
            }
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            raise ValidationError(f"Invalid JSON format: {e}") from e
        except Exception as e:
            logger.error(f"Failed to import JSON: {e}")
            raise ServiceError(f"Failed to import JSON: {e}") from e


class ExportService:
    """Service for exporting data to CSV/Markdown files."""

    @staticmethod
    def export_quotes_csv(
        session: Session,
        file_path: str | Path | None = None,
        filter_by: Optional[str] = None,
    ) -> str:
        """
        Export quotes to CSV format.

        Args:
            session: Database session
            file_path: Optional path to write file (if None, returns string)
            filter_by: Optional filter string for product names

        Returns:
            CSV string if no file_path provided, otherwise the file path
        """
        quotes = QuoteService.get_all(session, filter_by=filter_by, limit=10000)

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(
            [
                "id",
                "vendor",
                "product",
                "brand",
                "price",
                "total_cost",
                "currency",
                "shipping",
                "tax_rate",
                "status",
                "created_at",
            ]
        )

        # Data rows
        for q in quotes:
            writer.writerow(
                [
                    q.id,
                    q.vendor.name,
                    q.product.name,
                    q.product.brand.name,
                    f"{q.value:.2f}",
                    f"{q.total_cost:.2f}",
                    q.currency,
                    f"{q.shipping_cost:.2f}" if q.shipping_cost else "",
                    f"{q.tax_rate:.2f}" if q.tax_rate else "",
                    q.status or "",
                    str(q.created_at) if q.created_at else "",
                ]
            )

        csv_content = output.getvalue()

        if file_path:
            file_path = Path(file_path)
            file_path.write_text(csv_content, encoding="utf-8")
            logger.info(f"Exported {len(quotes)} quotes to {file_path}")
            return str(file_path)

        return csv_content

    @staticmethod
    def export_quotes_markdown(
        session: Session,
        file_path: str | Path | None = None,
        filter_by: Optional[str] = None,
        title: str = "Quote Report",
    ) -> str:
        """
        Export quotes to Markdown format.

        Args:
            session: Database session
            file_path: Optional path to write file (if None, returns string)
            filter_by: Optional filter string for product names
            title: Report title

        Returns:
            Markdown string if no file_path provided, otherwise the file path
        """
        quotes = QuoteService.get_all(session, filter_by=filter_by, limit=10000)

        lines = [
            f"# {title}",
            "",
            f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"Total quotes: {len(quotes)}",
            "",
            "| ID | Vendor | Product | Brand | Price | Total | Status |",
            "|---|---|---|---|---|---|---|",
        ]

        for q in quotes:
            status = q.status.capitalize() if q.status else "-"
            lines.append(
                f"| {q.id} | {q.vendor.name} | {q.product.name} | "
                f"{q.product.brand.name} | ${q.value:.2f} | ${q.total_cost:.2f} | {status} |"
            )

        # Summary section
        if quotes:
            prices = [q.value for q in quotes]
            lines.extend(
                [
                    "",
                    "## Summary",
                    "",
                    f"- **Total quotes:** {len(quotes)}",
                    f"- **Min price:** ${min(prices):.2f}",
                    f"- **Max price:** ${max(prices):.2f}",
                    f"- **Avg price:** ${sum(prices) / len(prices):.2f}",
                ]
            )

        md_content = "\n".join(lines)

        if file_path:
            file_path = Path(file_path)
            file_path.write_text(md_content, encoding="utf-8")
            logger.info(f"Exported {len(quotes)} quotes to {file_path}")
            return str(file_path)

        return md_content

    @staticmethod
    def export_products_csv(
        session: Session,
        file_path: str | Path | None = None,
    ) -> str:
        """Export products to CSV format."""
        products = ProductService.get_all(session, limit=10000)

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["id", "name", "brand", "category"])

        for p in products:
            writer.writerow([p.id, p.name, p.brand.name, p.category or ""])

        csv_content = output.getvalue()

        if file_path:
            file_path = Path(file_path)
            file_path.write_text(csv_content, encoding="utf-8")
            logger.info(f"Exported {len(products)} products to {file_path}")
            return str(file_path)

        return csv_content

    @staticmethod
    def export_vendors_csv(
        session: Session,
        file_path: str | Path | None = None,
    ) -> str:
        """Export vendors to CSV format."""
        vendors = VendorService.get_all(session, limit=10000)

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["id", "name", "currency", "discount_code", "discount"])

        for v in vendors:
            writer.writerow(
                [v.id, v.name, v.currency, v.discount_code or "", v.discount]
            )

        csv_content = output.getvalue()

        if file_path:
            file_path = Path(file_path)
            file_path.write_text(csv_content, encoding="utf-8")
            logger.info(f"Exported {len(vendors)} vendors to {file_path}")
            return str(file_path)

        return csv_content


class BackupService:
    """Service for database backup and restore operations."""

    @staticmethod
    def backup(
        db_path: str | Path,
        backup_path: str | Path | None = None,
    ) -> Path:
        """
        Create a backup of the database.

        Args:
            db_path: Path to the database file
            backup_path: Optional path for backup (defaults to db_path with timestamp)

        Returns:
            Path to the backup file
        """
        db_path = Path(db_path)
        if not db_path.exists():
            raise NotFoundError(f"Database not found: {db_path}")

        if backup_path is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = (
                db_path.parent / f"{db_path.stem}_backup_{timestamp}{db_path.suffix}"
            )
        else:
            backup_path = Path(backup_path)

        try:
            shutil.copy2(db_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise ServiceError(f"Failed to create backup: {e}") from e

    @staticmethod
    def restore(
        backup_path: str | Path,
        db_path: str | Path,
        create_backup: bool = True,
    ) -> Path:
        """
        Restore database from a backup.

        Args:
            backup_path: Path to the backup file
            db_path: Path where database should be restored
            create_backup: If True, backup current db before restoring

        Returns:
            Path to the restored database
        """
        backup_path = Path(backup_path)
        db_path = Path(db_path)

        if not backup_path.exists():
            raise NotFoundError(f"Backup not found: {backup_path}")

        # Create backup of current database if it exists
        if create_backup and db_path.exists():
            BackupService.backup(db_path)

        try:
            shutil.copy2(backup_path, db_path)
            logger.info(f"Restored database from {backup_path}")
            return db_path
        except Exception as e:
            logger.error(f"Failed to restore database: {e}")
            raise ServiceError(f"Failed to restore database: {e}") from e

    @staticmethod
    def list_backups(db_path: str | Path) -> List[Dict[str, Any]]:
        """
        List available backups for a database.

        Args:
            db_path: Path to the database file

        Returns:
            List of backup info dicts with path, size, and modified time
        """
        db_path = Path(db_path)
        backup_pattern = f"{db_path.stem}_backup_*{db_path.suffix}"
        backup_dir = db_path.parent

        backups: List[Dict[str, Any]] = []
        for backup_file in backup_dir.glob(backup_pattern):
            stat = backup_file.stat()
            backups.append(
                {
                    "path": backup_file,
                    "name": backup_file.name,
                    "size": stat.st_size,
                    "modified": datetime.datetime.fromtimestamp(stat.st_mtime),
                }
            )

        # Sort by modified time, newest first
        backups.sort(
            key=lambda b: b["modified"]
            if isinstance(b["modified"], datetime.datetime)
            else datetime.datetime.min,
            reverse=True,
        )
        return backups


class DeduplicationService:
    """Service for detecting and merging duplicate entities."""

    @staticmethod
    def find_similar_vendors(
        session: Session,
        threshold: float = 0.8,
    ) -> List[List[Vendor]]:
        """
        Find potentially duplicate vendors based on name similarity.

        Args:
            session: Database session
            threshold: Similarity threshold (0-1)

        Returns:
            List of groups of similar vendors
        """
        vendors = VendorService.get_all(session, limit=10000)
        groups = []
        processed = set()

        for i, v1 in enumerate(vendors):
            if v1.id in processed:
                continue

            similar = [v1]
            for v2 in vendors[i + 1 :]:
                if v2.id in processed:
                    continue
                if DeduplicationService._name_similarity(v1.name, v2.name) >= threshold:
                    similar.append(v2)
                    processed.add(v2.id)

            if len(similar) > 1:
                groups.append(similar)
                processed.add(v1.id)

        return groups

    @staticmethod
    def find_similar_products(
        session: Session,
        threshold: float = 0.8,
    ) -> List[List[Product]]:
        """
        Find potentially duplicate products based on name similarity.

        Args:
            session: Database session
            threshold: Similarity threshold (0-1)

        Returns:
            List of groups of similar products
        """
        products = ProductService.get_all(session, limit=10000)
        groups = []
        processed = set()

        for i, p1 in enumerate(products):
            if p1.id in processed:
                continue

            similar = [p1]
            for p2 in products[i + 1 :]:
                if p2.id in processed:
                    continue
                if DeduplicationService._name_similarity(p1.name, p2.name) >= threshold:
                    similar.append(p2)
                    processed.add(p2.id)

            if len(similar) > 1:
                groups.append(similar)
                processed.add(p1.id)

        return groups

    @staticmethod
    def _name_similarity(name1: str, name2: str) -> float:
        """
        Calculate similarity between two names (simple Jaccard similarity).

        Returns a value between 0 and 1.
        """
        # Normalize names
        n1 = name1.lower().strip()
        n2 = name2.lower().strip()

        if n1 == n2:
            return 1.0

        # Tokenize
        tokens1 = set(n1.split())
        tokens2 = set(n2.split())

        if not tokens1 or not tokens2:
            return 0.0

        # Jaccard similarity
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)

        return intersection / union if union > 0 else 0.0

    @staticmethod
    def merge_vendors(
        session: Session,
        keep_id: int,
        merge_ids: List[int],
    ) -> Vendor:
        """
        Merge multiple vendors into one, reassigning all quotes.

        Args:
            session: Database session
            keep_id: ID of vendor to keep
            merge_ids: IDs of vendors to merge (will be deleted)

        Returns:
            The kept Vendor instance
        """
        keep_vendor = session.get(Vendor, keep_id)
        if not keep_vendor:
            raise NotFoundError(f"Vendor {keep_id} not found")

        try:
            for merge_id in merge_ids:
                if merge_id == keep_id:
                    continue

                merge_vendor = session.get(Vendor, merge_id)
                if not merge_vendor:
                    continue

                # Reassign quotes
                for quote in merge_vendor.quotes:
                    quote.vendor_id = keep_id
                    quote.vendor = keep_vendor

                # Delete merged vendor
                session.delete(merge_vendor)

            session.commit()
            logger.info(f"Merged vendors {merge_ids} into {keep_id}")
            return keep_vendor
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to merge vendors: {e}")
            raise ServiceError(f"Failed to merge vendors: {e}") from e

    @staticmethod
    def merge_products(
        session: Session,
        keep_id: int,
        merge_ids: List[int],
    ) -> Product:
        """
        Merge multiple products into one, reassigning all quotes.

        Args:
            session: Database session
            keep_id: ID of product to keep
            merge_ids: IDs of products to merge (will be deleted)

        Returns:
            The kept Product instance
        """
        keep_product = session.get(Product, keep_id)
        if not keep_product:
            raise NotFoundError(f"Product {keep_id} not found")

        try:
            for merge_id in merge_ids:
                if merge_id == keep_id:
                    continue

                merge_product = session.get(Product, merge_id)
                if not merge_product:
                    continue

                # Reassign quotes
                for quote in merge_product.quotes:
                    quote.product_id = keep_id
                    quote.product = keep_product

                # Delete merged product
                session.delete(merge_product)

            session.commit()
            logger.info(f"Merged products {merge_ids} into {keep_id}")
            return keep_product
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to merge products: {e}")
            raise ServiceError(f"Failed to merge products: {e}") from e


class ClipboardService:
    """Service for clipboard operations."""

    @staticmethod
    def copy_quote(session: Session, quote_id: int) -> str:
        """
        Copy quote information to clipboard.

        Args:
            session: Database session
            quote_id: Quote ID

        Returns:
            String that was copied to clipboard
        """
        try:
            import pyperclip
        except ImportError:
            raise ServiceError("pyperclip is not installed. Run: pip install pyperclip")

        quote = (
            session.execute(
                select(Quote)
                .options(
                    joinedload(Quote.vendor),
                    joinedload(Quote.product).joinedload(Product.brand),
                )
                .where(Quote.id == quote_id)
            )
            .unique()
            .scalar_one_or_none()
        )

        if not quote:
            raise NotFoundError(f"Quote with ID {quote_id} not found")

        text = (
            f"Product: {quote.product.name}\n"
            f"Brand: {quote.product.brand.name}\n"
            f"Vendor: {quote.vendor.name}\n"
            f"Price: ${quote.value:.2f}\n"
            f"Total Cost: ${quote.total_cost:.2f}"
        )

        if quote.vendor.url:
            text += f"\nVendor URL: {quote.vendor.url}"

        try:
            pyperclip.copy(text)
            logger.info(f"Copied quote {quote_id} to clipboard")
            return text
        except Exception as e:
            raise ServiceError(f"Failed to copy to clipboard: {e}") from e

    @staticmethod
    def copy_product(session: Session, product_name: str) -> str:
        """
        Copy product information to clipboard.

        Args:
            session: Database session
            product_name: Product name

        Returns:
            String that was copied to clipboard
        """
        try:
            import pyperclip
        except ImportError:
            raise ServiceError("pyperclip is not installed. Run: pip install pyperclip")

        product = (
            session.execute(
                select(Product)
                .options(joinedload(Product.brand))
                .where(Product.name == product_name)
            )
            .unique()
            .scalar_one_or_none()
        )

        if not product:
            raise NotFoundError(f"Product '{product_name}' not found")

        # Get best price for product
        quotes = (
            session.execute(
                select(Quote)
                .options(joinedload(Quote.vendor))
                .where(Quote.product_id == product.id)
                .order_by(Quote.value.asc())
            )
            .unique()
            .scalars()
            .all()
        )

        text = f"Product: {product.name}\nBrand: {product.brand.name}"

        if product.category:
            text += f"\nCategory: {product.category}"

        if quotes:
            best = quotes[0]
            text += (
                f"\nBest Price: ${best.value:.2f} at {best.vendor.name}"
                f"\nTotal Quotes: {len(quotes)}"
            )

        try:
            pyperclip.copy(text)
            logger.info(f"Copied product '{product_name}' to clipboard")
            return text
        except Exception as e:
            raise ServiceError(f"Failed to copy to clipboard: {e}") from e

    @staticmethod
    def copy_vendor(session: Session, vendor_name: str) -> str:
        """
        Copy vendor information (including URL) to clipboard.

        Args:
            session: Database session
            vendor_name: Vendor name

        Returns:
            String that was copied to clipboard
        """
        try:
            import pyperclip
        except ImportError:
            raise ServiceError("pyperclip is not installed. Run: pip install pyperclip")

        vendor = Vendor.by_name(session, vendor_name)
        if not vendor:
            raise NotFoundError(f"Vendor '{vendor_name}' not found")

        text = f"Vendor: {vendor.name}\nCurrency: {vendor.currency}"

        if vendor.url:
            text += f"\nURL: {vendor.url}"

        if vendor.discount_code:
            text += f"\nDiscount Code: {vendor.discount_code}"

        if vendor.discount > 0:
            text += f"\nDiscount: {vendor.discount}%"

        try:
            pyperclip.copy(text)
            logger.info(f"Copied vendor '{vendor_name}' to clipboard")
            return text
        except Exception as e:
            raise ServiceError(f"Failed to copy to clipboard: {e}") from e


class VendorURLService:
    """Service for vendor URL operations."""

    @staticmethod
    def set_url(session: Session, vendor_name: str, url: str) -> Vendor:
        """
        Set or update a vendor's URL.

        Args:
            session: Database session
            vendor_name: Vendor name
            url: URL to set

        Returns:
            Updated Vendor instance
        """
        url = url.strip()
        if not url:
            raise ValidationError("URL cannot be empty")

        # Basic URL validation
        if not url.startswith(("http://", "https://")):
            raise ValidationError("URL must start with http:// or https://")

        vendor = Vendor.by_name(session, vendor_name)
        if not vendor:
            raise NotFoundError(f"Vendor '{vendor_name}' not found")

        try:
            vendor.url = url
            session.commit()
            logger.info(f"Set URL for vendor '{vendor_name}': {url}")
            return vendor
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to set vendor URL: {e}")
            raise ServiceError(f"Failed to set vendor URL: {e}") from e

    @staticmethod
    def open_url(session: Session, vendor_name: str) -> str:
        """
        Open a vendor's URL in the default browser.

        Args:
            session: Database session
            vendor_name: Vendor name

        Returns:
            The URL that was opened
        """
        import webbrowser

        vendor = Vendor.by_name(session, vendor_name)
        if not vendor:
            raise NotFoundError(f"Vendor '{vendor_name}' not found")

        if not vendor.url:
            raise ValidationError(f"Vendor '{vendor_name}' has no URL set")

        try:
            webbrowser.open(vendor.url)
            logger.info(f"Opened URL for vendor '{vendor_name}': {vendor.url}")
            return vendor.url
        except Exception as e:
            raise ServiceError(f"Failed to open URL: {e}") from e

    @staticmethod
    def clear_url(session: Session, vendor_name: str) -> Vendor:
        """
        Clear a vendor's URL.

        Args:
            session: Database session
            vendor_name: Vendor name

        Returns:
            Updated Vendor instance
        """
        vendor = Vendor.by_name(session, vendor_name)
        if not vendor:
            raise NotFoundError(f"Vendor '{vendor_name}' not found")

        try:
            vendor.url = None
            session.commit()
            logger.info(f"Cleared URL for vendor '{vendor_name}'")
            return vendor
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to clear vendor URL: {e}")
            raise ServiceError(f"Failed to clear vendor URL: {e}") from e


class ReceiptService:
    """Service for receipt attachment operations."""

    @staticmethod
    def attach(session: Session, quote_id: int, file_path: str | Path) -> Quote:
        """
        Attach a receipt file to a quote.

        Args:
            session: Database session
            quote_id: Quote ID
            file_path: Path to receipt file

        Returns:
            Updated Quote instance
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise NotFoundError(f"Receipt file not found: {file_path}")

        quote = session.get(Quote, quote_id)
        if not quote:
            raise NotFoundError(f"Quote with ID {quote_id} not found")

        try:
            quote.receipt_path = str(file_path.absolute())
            session.commit()
            logger.info(f"Attached receipt to quote {quote_id}: {file_path}")
            return quote
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to attach receipt: {e}")
            raise ServiceError(f"Failed to attach receipt: {e}") from e

    @staticmethod
    def open(session: Session, quote_id: int) -> str:
        """
        Open a quote's receipt file.

        Args:
            session: Database session
            quote_id: Quote ID

        Returns:
            Path to the receipt that was opened
        """
        import subprocess
        import platform

        quote = session.get(Quote, quote_id)
        if not quote:
            raise NotFoundError(f"Quote with ID {quote_id} not found")

        if not quote.receipt_path:
            raise ValidationError(f"Quote {quote_id} has no receipt attached")

        receipt_path = Path(quote.receipt_path)
        if not receipt_path.exists():
            raise NotFoundError(f"Receipt file not found: {receipt_path}")

        try:
            system = platform.system()
            if system == "Darwin":  # macOS
                subprocess.run(["open", str(receipt_path)], check=True)
            elif system == "Windows":
                subprocess.run(["start", "", str(receipt_path)], shell=True, check=True)
            else:  # Linux
                subprocess.run(["xdg-open", str(receipt_path)], check=True)

            logger.info(f"Opened receipt for quote {quote_id}: {receipt_path}")
            return str(receipt_path)
        except subprocess.CalledProcessError as e:
            raise ServiceError(f"Failed to open receipt: {e}") from e

    @staticmethod
    def detach(session: Session, quote_id: int) -> Quote:
        """
        Remove receipt attachment from a quote.

        Args:
            session: Database session
            quote_id: Quote ID

        Returns:
            Updated Quote instance
        """
        quote = session.get(Quote, quote_id)
        if not quote:
            raise NotFoundError(f"Quote with ID {quote_id} not found")

        try:
            quote.receipt_path = None
            session.commit()
            logger.info(f"Detached receipt from quote {quote_id}")
            return quote
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to detach receipt: {e}")
            raise ServiceError(f"Failed to detach receipt: {e}") from e

    @staticmethod
    def get_quotes_with_receipts(session: Session) -> List[Quote]:
        """
        Get all quotes that have receipts attached.

        Returns:
            List of Quote instances with receipts
        """
        results = (
            session.execute(
                select(Quote)
                .options(
                    joinedload(Quote.vendor),
                    joinedload(Quote.product).joinedload(Product.brand),
                )
                .where(Quote.receipt_path.isnot(None))
                .order_by(Quote.created_at.desc())
            )
            .unique()
            .scalars()
            .all()
        )
        return list(results)


class ScraperService:
    """Service for web scraping product prices."""

    @staticmethod
    def scrape_price(url: str) -> Dict[str, Any]:
        """
        Attempt to scrape a product price from a URL.

        Args:
            url: URL to scrape

        Returns:
            Dict with scraped data (price, currency, title, etc.)
        """
        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError:
            raise ServiceError(
                "Web scraping requires requests and beautifulsoup4. "
                "Run: pip install requests beautifulsoup4"
            )

        if not url.startswith(("http://", "https://")):
            raise ValidationError("URL must start with http:// or https://")

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            raise ServiceError(f"Failed to fetch URL: {e}") from e

        soup = BeautifulSoup(response.text, "html.parser")

        result = {
            "url": url,
            "title": None,
            "price": None,
            "currency": "USD",
            "raw_price": None,
        }

        # Try to extract title
        title_tag = soup.find("title")
        if title_tag:
            result["title"] = title_tag.text.strip()

        # Try to extract price using common patterns
        price = ScraperService._extract_price(soup)
        if price:
            result["price"] = price["value"]
            result["currency"] = price.get("currency", "USD")
            result["raw_price"] = price.get("raw")

        logger.info(f"Scraped price from {url}: {result}")
        return result

    @staticmethod
    def _extract_price(soup) -> Optional[Dict[str, Any]]:
        """
        Try to extract price from HTML using common patterns.

        Returns dict with 'value', 'currency', and 'raw' keys, or None if not found.
        """
        import re

        # Common price selectors to try
        price_selectors = [
            # JSON-LD structured data
            {"type": "json-ld"},
            # Meta tags
            {"name": "meta", "attrs": {"property": "product:price:amount"}},
            {"name": "meta", "attrs": {"property": "og:price:amount"}},
            # Common class patterns
            {"class_": re.compile(r"price|Price|priceblock|priceToPay", re.I)},
            {"itemprop": "price"},
            {"data-price": True},
        ]

        # Try JSON-LD first
        for script in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                import json

                data = json.loads(script.string)
                if isinstance(data, dict):
                    price = ScraperService._extract_from_jsonld(data)
                    if price:
                        return price
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            price = ScraperService._extract_from_jsonld(item)
                            if price:
                                return price
            except (json.JSONDecodeError, TypeError):
                continue

        # Try meta tags
        for selector in price_selectors[1:3]:
            tag = soup.find(**selector)
            if tag and tag.get("content"):
                try:
                    return {
                        "value": float(tag["content"]),
                        "currency": "USD",
                        "raw": tag["content"],
                    }
                except ValueError:
                    continue

        # Try common class patterns
        price_pattern = re.compile(r"\$?\d+(?:,\d{3})*(?:\.\d{2})?")

        for selector in price_selectors[3:]:
            elements = soup.find_all(**selector)
            for elem in elements:
                text = elem.get_text(strip=True)
                match = price_pattern.search(text)
                if match:
                    raw = match.group()
                    # Remove currency symbols and commas
                    clean = re.sub(r"[\$\£\?,]", "", raw)
                    try:
                        value = float(clean)
                        currency = "USD"
                        if "\u00a3" in text or "GBP" in text:
                            currency = "GBP"
                        elif "\u20ac" in text or "EUR" in text:
                            currency = "EUR"
                        return {"value": value, "currency": currency, "raw": raw}
                    except ValueError:
                        continue

        return None

    @staticmethod
    def _extract_from_jsonld(data: dict) -> Optional[Dict[str, Any]]:
        """Extract price from JSON-LD structured data."""
        # Check for Product type
        if data.get("@type") == "Product":
            offers = data.get("offers", {})
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            price = offers.get("price")
            if price:
                try:
                    return {
                        "value": float(price),
                        "currency": offers.get("priceCurrency", "USD"),
                        "raw": str(price),
                    }
                except ValueError:
                    pass

        # Check for Offer type
        if data.get("@type") == "Offer":
            price = data.get("price")
            if price:
                try:
                    return {
                        "value": float(price),
                        "currency": data.get("priceCurrency", "USD"),
                        "raw": str(price),
                    }
                except ValueError:
                    pass

        return None

    @staticmethod
    def create_quote_from_scrape(
        session: Session,
        url: str,
        vendor_name: str,
        product_name: str,
        brand_name: Optional[str] = None,
    ) -> Quote:
        """
        Scrape a URL and create a quote from the result.

        Args:
            session: Database session
            url: URL to scrape
            vendor_name: Vendor name
            product_name: Product name
            brand_name: Optional brand name for new products

        Returns:
            Created Quote instance
        """
        scraped = ScraperService.scrape_price(url)

        if not scraped.get("price"):
            raise ValidationError(f"Could not extract price from {url}")

        # Use scraped price
        price = scraped["price"]

        # Get vendor
        vendor = Vendor.by_name(session, vendor_name)
        if not vendor:
            raise NotFoundError(f"Vendor '{vendor_name}' not found")

        # Set vendor URL if not already set
        if not vendor.url:
            # Extract base URL
            from urllib.parse import urlparse

            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            vendor.url = base_url

        # Get or create product
        product = Product.by_name(session, product_name)
        if not product:
            if not brand_name:
                raise ValidationError(
                    f"Product '{product_name}' not found and no brand name provided"
                )
            product = ProductService.create(session, product_name, brand_name)

        # Create quote
        try:
            quote = Quote(
                vendor=vendor,
                product=product,
                currency="USD",  # Prices are stored in USD
                value=price,
            )
            session.add(quote)
            session.commit()
            logger.info(f"Created quote from scraped URL: {url}")
            return quote
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to create quote from scrape: {e}")
            raise ServiceError(f"Failed to create quote: {e}") from e


class ReportService:
    """Service for generating HTML reports."""

    # CSS styles for reports
    CSS = """
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
            border-bottom: 2px solid #2c3e50;
            padding-bottom: 10px;
        }
        h2 {
            color: #2c3e50;
            margin-top: 30px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background-color: white;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #2c3e50;
            color: white;
            font-weight: 600;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .best-price {
            background-color: #d4edda;
            font-weight: bold;
        }
        .status-considering {
            background-color: #fff3cd;
        }
        .status-ordered {
            background-color: #cce5ff;
        }
        .status-received {
            background-color: #d4edda;
        }
        .summary-box {
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .summary-item {
            display: inline-block;
            margin-right: 30px;
            padding: 10px;
        }
        .summary-label {
            color: #666;
            font-size: 0.9em;
        }
        .summary-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #2c3e50;
        }
        .discount-code {
            background-color: #e7f5ff;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: monospace;
        }
        .savings {
            color: #28a745;
            font-weight: bold;
        }
        .text-muted {
            color: #6c757d;
        }
        @media print {
            body { background-color: white; }
            table { box-shadow: none; }
            .summary-box { box-shadow: none; border: 1px solid #ddd; }
        }
    """

    @staticmethod
    def _html_header(title: str) -> str:
        """Generate HTML header with CSS styles."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>{ReportService.CSS}</style>
</head>
<body>
    <h1>{title}</h1>
    <p class="text-muted">Generated: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
"""

    @staticmethod
    def _html_footer() -> str:
        """Generate HTML footer."""
        return """
</body>
</html>
"""

    @staticmethod
    def _html_table(
        headers: List[str],
        rows: List[List[str]],
        row_classes: Optional[List[str]] = None,
    ) -> str:
        """Generate an HTML table."""
        html = "<table>\n<thead>\n<tr>"
        for h in headers:
            html += f"<th>{h}</th>"
        html += "</tr>\n</thead>\n<tbody>\n"

        for i, row in enumerate(rows):
            row_class = row_classes[i] if row_classes and i < len(row_classes) else ""
            class_attr = f' class="{row_class}"' if row_class else ""
            html += f"<tr{class_attr}>"
            for cell in row:
                html += f"<td>{cell}</td>"
            html += "</tr>\n"

        html += "</tbody>\n</table>\n"
        return html

    @staticmethod
    def _escape_html(text: str) -> str:
        """Escape HTML special characters."""
        if text is None:
            return ""
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    @staticmethod
    def price_comparison_report(
        session: Session, filter_term: Optional[str] = None
    ) -> str:
        """
        Generate a price comparison report.

        Args:
            session: Database session
            filter_term: Optional filter term for products

        Returns:
            HTML string of the report
        """
        # Get products with quotes
        if filter_term:
            products = (
                session.execute(
                    select(Product)
                    .options(
                        joinedload(Product.brand),
                        joinedload(Product.quotes).joinedload(Quote.vendor),
                    )
                    .where(Product.name.ilike(f"%{filter_term}%"))
                    .order_by(Product.name)
                )
                .unique()
                .scalars()
                .all()
            )
        else:
            products = (
                session.execute(
                    select(Product)
                    .options(
                        joinedload(Product.brand),
                        joinedload(Product.quotes).joinedload(Quote.vendor),
                    )
                    .order_by(Product.name)
                )
                .unique()
                .scalars()
                .all()
            )

        title = "Price Comparison Report"
        if filter_term:
            title += f" - '{ReportService._escape_html(filter_term)}'"

        html = ReportService._html_header(title)

        # Summary
        total_products = len([p for p in products if p.quotes])
        total_quotes = sum(len(p.quotes) for p in products)
        html += f"""
    <div class="summary-box">
        <div class="summary-item">
            <div class="summary-label">Products</div>
            <div class="summary-value">{total_products}</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">Total Quotes</div>
            <div class="summary-value">{total_quotes}</div>
        </div>
    </div>
"""

        # Product comparisons
        for product in products:
            if not product.quotes:
                continue

            quotes = sorted(product.quotes, key=lambda q: q.value)
            best_price = quotes[0].value if quotes else None
            worst_price = quotes[-1].value if quotes else None

            html += f"<h2>{ReportService._escape_html(product.brand.name)} {ReportService._escape_html(product.name)}</h2>\n"

            if product.category:
                html += f"<p class='text-muted'>Category: {ReportService._escape_html(product.category)}</p>\n"

            headers = [
                "Vendor",
                "Price (USD)",
                "Total Cost",
                "Discount Code",
                "Savings vs Worst",
            ]
            rows = []
            row_classes = []

            for q in quotes:
                discount_code = ""
                if q.vendor.discount_code:
                    discount_code = f"<span class='discount-code'>{ReportService._escape_html(q.vendor.discount_code)}</span> ({q.vendor.discount}%)"

                savings = ""
                if worst_price and best_price and worst_price > best_price:
                    savings_amount = worst_price - q.value
                    if savings_amount > 0:
                        savings = f"<span class='savings'>${savings_amount:.2f}</span>"

                rows.append(
                    [
                        ReportService._escape_html(q.vendor.name),
                        f"${q.value:.2f}",
                        f"${q.total_cost:.2f}",
                        discount_code or "-",
                        savings or "-",
                    ]
                )
                row_classes.append("best-price" if q.value == best_price else "")

            html += ReportService._html_table(headers, rows, row_classes)

            # Price spread summary
            if best_price and worst_price:
                spread = worst_price - best_price
                html += f"""
    <p>
        Best: <strong>${best_price:.2f}</strong> |
        Worst: <strong>${worst_price:.2f}</strong> |
        Potential Savings: <span class="savings">${spread:.2f}</span>
    </p>
"""

        html += ReportService._html_footer()
        return html

    @staticmethod
    def purchase_summary_report(session: Session) -> str:
        """
        Generate a purchase summary report grouped by status.

        Args:
            session: Database session

        Returns:
            HTML string of the report
        """
        html = ReportService._html_header("Purchase Summary Report")

        status_totals: Dict[str, Dict[str, Any]] = {}
        all_quotes: List[Quote] = []

        for status in QUOTE_STATUSES:
            quotes = (
                session.execute(
                    select(Quote)
                    .options(
                        joinedload(Quote.vendor),
                        joinedload(Quote.product).joinedload(Product.brand),
                    )
                    .where(Quote.status == status)
                    .order_by(Quote.created_at.desc())
                )
                .unique()
                .scalars()
                .all()
            )
            status_totals[status] = {
                "count": len(quotes),
                "total": sum(q.total_cost for q in quotes),
                "quotes": list(quotes),
            }
            all_quotes.extend(quotes)

        # Summary box
        total_considering: float = status_totals["considering"]["total"]
        total_ordered: float = status_totals["ordered"]["total"]
        total_received: float = status_totals["received"]["total"]
        total_all = total_considering + total_ordered + total_received

        html += f"""
    <div class="summary-box">
        <div class="summary-item">
            <div class="summary-label">Considering</div>
            <div class="summary-value">${total_considering:.2f}</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">Ordered</div>
            <div class="summary-value">${total_ordered:.2f}</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">Received</div>
            <div class="summary-value">${total_received:.2f}</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">Grand Total</div>
            <div class="summary-value">${total_all:.2f}</div>
        </div>
    </div>
"""

        # Status sections
        status_labels = {
            "considering": "Under Consideration",
            "ordered": "Ordered",
            "received": "Received",
        }

        for status in QUOTE_STATUSES:
            data = status_totals[status]
            quotes_list: List[Quote] = data["quotes"]
            if not quotes_list:
                continue

            html += f"<h2>{status_labels[status]} ({data['count']} items - ${data['total']:.2f})</h2>\n"

            headers = ["Product", "Vendor", "Price", "Total Cost", "Date"]
            rows = []
            row_classes = []

            for q in quotes_list:
                rows.append(
                    [
                        f"{ReportService._escape_html(q.product.brand.name)} {ReportService._escape_html(q.product.name)}",
                        ReportService._escape_html(q.vendor.name),
                        f"${q.value:.2f}",
                        f"${q.total_cost:.2f}",
                        q.created_at.strftime("%Y-%m-%d") if q.created_at else "-",
                    ]
                )
                row_classes.append(f"status-{status}")

            html += ReportService._html_table(headers, rows, row_classes)

        html += ReportService._html_footer()
        return html

    @staticmethod
    def vendor_analysis_report(session: Session) -> str:
        """
        Generate a vendor analysis report.

        Args:
            session: Database session

        Returns:
            HTML string of the report
        """
        vendors = (
            session.execute(
                select(Vendor).options(joinedload(Vendor.quotes)).order_by(Vendor.name)
            )
            .unique()
            .scalars()
            .all()
        )

        html = ReportService._html_header("Vendor Analysis Report")

        # Summary
        total_vendors = len(vendors)
        vendors_with_quotes = len([v for v in vendors if v.quotes])
        total_quotes = sum(len(v.quotes) for v in vendors)

        html += f"""
    <div class="summary-box">
        <div class="summary-item">
            <div class="summary-label">Total Vendors</div>
            <div class="summary-value">{total_vendors}</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">With Quotes</div>
            <div class="summary-value">{vendors_with_quotes}</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">Total Quotes</div>
            <div class="summary-value">{total_quotes}</div>
        </div>
    </div>
"""

        # Vendor table
        html += "<h2>Vendor Details</h2>\n"
        headers = [
            "Vendor",
            "Currency",
            "Quotes",
            "Avg Price",
            "Total Value",
            "Discount Code",
        ]
        rows = []

        for v in vendors:
            quote_count = len(v.quotes)
            if quote_count > 0:
                avg_price = sum(q.value for q in v.quotes) / quote_count
                total_value = sum(q.total_cost for q in v.quotes)
            else:
                avg_price = 0
                total_value = 0

            discount_info = ""
            if v.discount_code:
                discount_info = f"<span class='discount-code'>{ReportService._escape_html(v.discount_code)}</span> ({v.discount}%)"

            rows.append(
                [
                    ReportService._escape_html(v.name),
                    v.currency,
                    str(quote_count),
                    f"${avg_price:.2f}" if quote_count > 0 else "-",
                    f"${total_value:.2f}" if quote_count > 0 else "-",
                    discount_info or "-",
                ]
            )

        html += ReportService._html_table(headers, rows)

        # Currency breakdown
        currency_stats: Dict[str, Dict[str, Any]] = {}
        for v in vendors:
            if v.currency not in currency_stats:
                currency_stats[v.currency] = {"vendors": 0, "quotes": 0, "total": 0.0}
            currency_stats[v.currency]["vendors"] += 1
            currency_stats[v.currency]["quotes"] += len(v.quotes)
            currency_stats[v.currency]["total"] += sum(q.total_cost for q in v.quotes)

        html += "<h2>Currency Breakdown</h2>\n"
        headers = ["Currency", "Vendors", "Quotes", "Total Value (USD)"]
        rows = []
        for currency, stats in sorted(currency_stats.items()):
            rows.append(
                [
                    currency,
                    str(stats["vendors"]),
                    str(stats["quotes"]),
                    f"${stats['total']:.2f}",
                ]
            )
        html += ReportService._html_table(headers, rows)

        html += ReportService._html_footer()
        return html

    @staticmethod
    def generate_report(
        session: Session, preset: str, output_file: Optional[str] = None, **kwargs
    ) -> str:
        """
        Generate a report using the specified preset.

        Args:
            session: Database session
            preset: Report preset ('price-comparison', 'purchase-summary', 'vendor-analysis')
            output_file: Optional output file path
            **kwargs: Additional arguments for specific reports

        Returns:
            HTML string (or file path if output_file specified)
        """
        if preset == "price-comparison":
            html = ReportService.price_comparison_report(
                session, filter_term=kwargs.get("filter_term")
            )
        elif preset == "purchase-summary":
            html = ReportService.purchase_summary_report(session)
        elif preset == "vendor-analysis":
            html = ReportService.vendor_analysis_report(session)
        else:
            raise ValidationError(
                f"Unknown report preset: {preset}. "
                "Valid options: price-comparison, purchase-summary, vendor-analysis"
            )

        if output_file:
            output_path = Path(output_file)
            output_path.write_text(html, encoding="utf-8")
            logger.info(f"Generated {preset} report: {output_file}")
            return str(output_path)

        return html
