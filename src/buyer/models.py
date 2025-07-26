#!/usr/bin/env python3
"""model.py: models a purchasing support tool"""
from contextlib import contextmanager
from pathlib import Path
from typing import List

from sqlalchemy import (Column, Date, DateTime, Float, ForeignKey, Integer,
                        String, Table, create_engine)
from sqlalchemy import exc
from sqlalchemy import select
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import relationship, sessionmaker, mapped_column
from sqlalchemy.orm import DeclarativeBase, Mapped
from sqlalchemy.sql import func



class Base(DeclarativeBase):
    pass



class Object:
    """A mixin class for sqlalcheny to save some typing"""
    @declared_attr.directive
    def __tablename__(cls):
        return cls.__name__.lower()

    @classmethod
    def by_name(cls, session, name):
        """query table by name"""
        stmt = select(cls).where(cls.name == name)
        return session.execute(stmt).scalar_one_or_none()

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)

    def __repr__(self):
        return f"<{self.__class__.__name__}(name='{self.name}')>"


class Forex(Base):
    """Table of fx to usd to fx rates"""
    __tablename__ = 'forex'

    id: Mapped[int] = mapped_column(primary_key=True)
    # date = mapped_column(Date, default=func.now())
    code: Mapped[str] = mapped_column(String)
    units_per_usd: Mapped[float] = mapped_column(Float)
    usd_per_unit: Mapped[float]  = mapped_column(Float)

    def __repr__(self):
        return f"<Forex(USD -> {self.code}: {self.units_per_usd})>"


VendorBrand = Table(
    'vendor_brand', Base.metadata,
    Column('vendor_id', ForeignKey('vendor.id'), primary_key=True),
    Column('brand_id', ForeignKey('brand.id'), primary_key=True))


class Vendor(Object, Base):
    """Selling Entity"""

    #country = mapped_column(String)
    currency: Mapped[str] = mapped_column(String)
    discount_code: Mapped[str | None] = mapped_column(String)
    discount: Mapped[float] = mapped_column(Float, default=0.0)
    brands: Mapped[List["Brand"]] = relationship(secondary=VendorBrand, back_populates='vendors')
    quotes: Mapped[List["Quote"]] = relationship(back_populates='vendor')

    def add_product(self,
                    session,
                    brand_name,
                    product_name,
                    price,
                    discount=0.0):
        _brand = session.execute(select(Brand).where(Brand.name == brand_name)).scalar_one_or_none()
        _product = session.execute(select(Product).where(Product.name == product_name)).scalar_one_or_none()

        if not _brand:
            _brand = Brand(name=brand_name)
            self.brands.append(_brand)
            session.add(_brand)

        if not _product:
            _product = Product(name=product_name, brand=_brand)
            session.add(_product)

        if _brand and _product:
            _quote = Quote(product=_product,
                           vendor=self,
                           currency=self.currency,
                           value=price,
                           discount=discount)
            session.add(_quote)


class Brand(Object, Base):
    """Manufacturing Entity"""
    vendors: Mapped[List["Vendor"]] = relationship('Vendor', secondary=VendorBrand, back_populates='brands')
    products: Mapped[List["Product"]] = relationship('Product', back_populates='brand')


class Product(Object, Base):
    """Item sold by brand via vendor"""
    brand_id: Mapped[int] = mapped_column(Integer, ForeignKey('brand.id'))
    brand: Mapped["Brand"] = relationship('Brand', back_populates='products')
    quotes: Mapped[List["Quote"]] = relationship('Quote', back_populates='product')


class Quote(Base):
    """Quoted Quote of Item from a vendor"""
    __tablename__ = 'quote'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # time_created = mapped_column(DateTime(timezone=True), default=func.now())
    # date_created = mapped_column(Date, default=func.now())
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey('product.id'))
    product: Mapped["Product"] = relationship('Product', back_populates='quotes')
    vendor_id: Mapped[int] = mapped_column(Integer, ForeignKey('vendor.id'))
    vendor: Mapped["Vendor"] = relationship('Vendor', back_populates='quotes')
    currency: Mapped[str] = mapped_column(String, default='USD')
    value: Mapped[float] = mapped_column(Float)
    discount: Mapped[float] = mapped_column(Float, default=0.0)

    def __repr__(self):
        return f"<Quote({self.vendor.name} / {self.product.brand.name} {self.product.name} / {self.value} {self.currency})>"



if __name__ == '__main__':
    engine = create_engine('sqlite:///:memory:')
    Session = sessionmaker(bind=engine)
    session = Session()

    Base.metadata.create_all(engine)

    # fx
    eur = Forex(code='EUR', units_per_usd=0.921, usd_per_unit=1.085)
    gbp = Forex(code='GBP', units_per_usd=0.773, usd_per_unit=1.292)

    # brands
    apple = Brand(name='Apple')
    session.add(apple)

    # products
    iphone_15 = Product(name='iPhone 15', brand=apple)
    session.add(iphone_15)
    iphone_14 = Product(name='iPhone 14', brand=apple)
    session.add(iphone_14)

    # vendors
    apple_shop_nyc = Vendor(name='Apple Shop NYC', currency='USD')
    session.add(apple_shop_nyc)

    # quotes
    q1 = Quote(product=iphone_15, vendor=apple_shop_nyc, currency='USD', value=1200)
    session.add(q1)
    q2 = Quote(product=iphone_14, vendor=apple_shop_nyc, currency='USD', value=1000)
    session.add(q2)

    # add products
    apple_shop_nyc.add_product(session, 'Apple', 'iPhone 13', 100)


    session.commit()

    print("brands:", session.query(Brand).all())
    print("products:", session.query(Product).all())
    print("vendors:", session.query(Vendor).all())
    print("quotes:", session.query(Quote).all())
