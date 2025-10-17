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

from .models import Brand, Product, Vendor, Quote, Forex
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
