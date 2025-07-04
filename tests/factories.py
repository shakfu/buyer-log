import random
import string

import factory
import factory.fuzzy

# from . import models
import buyer.models as models

ALPHANUM = string.ascii_letters + string.digits


class BrandFactory(factory.alchemy.SQLAlchemyModelFactory):
    id = factory.Sequence(lambda n: '%s' % n)
    name = factory.Faker('company')

    class Meta:
        model = models.Brand


class ProductFactory(factory.alchemy.SQLAlchemyModelFactory):
    id = factory.Sequence(lambda n: '%s' % n)
    name = factory.Faker('word')
    brand = factory.SubFactory(BrandFactory)

    class Meta:
        model = models.Product


class VendorFactory(factory.alchemy.SQLAlchemyModelFactory):
    id = factory.Sequence(lambda n: '%s' % n)
    name = factory.Faker('company')
    currency = factory.Faker('currency_code')
    discount_code = factory.fuzzy.FuzzyText(length=8, chars=ALPHANUM)
    discount = factory.fuzzy.FuzzyFloat(0.05, 0.15)

    class Meta:
        model = models.Vendor


class QuoteFactory(factory.alchemy.SQLAlchemyModelFactory):
    id = factory.Sequence(lambda n: '%s' % n)
    date_created = factory.Faker('date_this_decade')
    currency = factory.Faker('currency_code')
    discount = factory.fuzzy.FuzzyFloat(0.05, 0.15)
    value = factory.fuzzy.FuzzyFloat(50.0, 1000.0)
    product = factory.SubFactory(ProductFactory)
    vendor = factory.SubFactory(VendorFactory)

    class Meta:
        model = models.Quote
