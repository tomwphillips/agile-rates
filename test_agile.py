from datetime import datetime, timezone

import responses

from agile import (API_BASE_URL, Product, Tariff, UnitRate, get_tariffs,
                   get_unit_rates, list_products)


@responses.activate()
def test_list_products():
    responses.get(
        API_BASE_URL + "/products/",
        json={
            "results": [
                {"code": "AGILE-1", "brand": "OCTOPUS_ENERGY", "direction": "IMPORT"},
                {"code": "AGILE-2", "brand": "STARFISH_ENERGY"},
                {"code": "STIFF-1", "brand": "OCTOPUS_ENERGY"},
            ]
        },
    )
    products = list_products()
    assert products == [Product(code="AGILE-1")]


@responses.activate()
def test_get_tariffs():
    responses.get(
        API_BASE_URL + "/products/PRODUCT-1",
        json={
            "code": "PRODUCT-1",
            "single_register_electricity_tariffs": {
                "_A": {"direct_debit_monthly": {"code": "A-1"}},
                "_B": {"direct_debit_monthly": {"code": "B-1"}},
            },
        },
    )
    tariffs = get_tariffs(Product(code="PRODUCT-1"))
    assert tariffs == [
        Tariff(code="A-1", product_code="PRODUCT-1"),
        Tariff(code="B-1", product_code="PRODUCT-1"),
    ]


@responses.activate()
def test_get_unit_rates():
    responses.get(
        API_BASE_URL
        + "/products/PRODUCT-CODE/electricity-tariffs/TARIFF-CODE/standard-unit-rates/",
        json={
            "count": 7724,
            "next": None,
            "previous": None,
            "results": [
                {
                    "value_exc_vat": 7.78,
                    "value_inc_vat": 8.169,
                    "valid_from": "2023-04-10T21:30:00Z",
                    "valid_to": "2023-04-10T22:00:00Z",
                },
                {
                    "value_exc_vat": 15.84,
                    "value_inc_vat": 16.632,
                    "valid_from": "2023-04-10T21:00:00Z",
                    "valid_to": "2023-04-10T21:30:00Z",
                },
            ],
        },
    )
    unit_rates = get_unit_rates(Tariff(code="TARIFF-CODE", product_code="PRODUCT-CODE"))
    assert unit_rates == [
        UnitRate(
            valid_from=datetime(2023, 4, 10, 21, 30, tzinfo=timezone.utc),
            valid_to=datetime(2023, 4, 10, 22, 0, tzinfo=timezone.utc),
            value_exc_vat=7.78,
            value_inc_vat=8.169,
        ),
        UnitRate(
            valid_from=datetime(2023, 4, 10, 21, 0, tzinfo=timezone.utc),
            valid_to=datetime(2023, 4, 10, 21, 30, tzinfo=timezone.utc),
            value_exc_vat=15.84,
            value_inc_vat=16.632,
        ),
    ]
