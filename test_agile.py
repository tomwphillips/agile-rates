from datetime import datetime, date, timezone, timedelta
import pytest

import responses

from agile import (
    API_BASE_URL,
    Product,
    Tariff,
    UnitRate,
    get_tariffs,
    get_unit_rates,
    list_products,
)


@responses.activate()
def test_list_products():
    url = API_BASE_URL + "/products/"

    responses.get(
        url,
        json={
            "next": url + "?page=2",
            "results": [
                {"code": "AGILE-2", "brand": "STARFISH_ENERGY"},
                {"code": "STIFF-1", "brand": "OCTOPUS_ENERGY"},
            ],
        },
        match=[responses.matchers.query_param_matcher({})],
    )

    responses.get(
        url,
        json={
            "next": None,
            "results": [
                {"code": "AGILE-1", "brand": "OCTOPUS_ENERGY", "direction": "IMPORT"},
            ],
        },
        match=[responses.matchers.query_param_matcher({"page": 2})],
    )

    products = list(list_products())
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
    url = (
        API_BASE_URL
        + "/products/PRODUCT-CODE/electricity-tariffs/TARIFF-CODE/standard-unit-rates/"
    )

    responses.get(
        url,
        json={
            "count": 2,
            "next": None,
            "previous": None,
            "results": [
                {
                    "value_exc_vat": 7.78,
                    "value_inc_vat": 8.169,
                    "valid_from": "2023-04-10T00:00:00Z",
                    "valid_to": "2023-04-10T00:30:00Z",
                },
                {
                    "value_exc_vat": 15.84,
                    "value_inc_vat": 16.632,
                    "valid_from": "2023-04-10T23:30:00Z",
                    "valid_to": "2023-04-11T00:00:00Z",
                },
            ],
        },
        match=[
            responses.matchers.query_param_matcher(
                {
                    "period_from": "2023-04-10T00:00:00Z",
                    "period_to": "2023-04-11T00:00:00Z",
                }
            )
        ],
    )

    unit_rates = list(
        get_unit_rates(
            Tariff(code="TARIFF-CODE", product_code="PRODUCT-CODE"),
            date_from=date(2023, 4, 10),
            date_to=date(2023, 4, 11),
        )
    )
    assert unit_rates == [
        UnitRate(
            valid_from=datetime(2023, 4, 10, 0, 0, tzinfo=timezone.utc),
            valid_to=datetime(2023, 4, 10, 0, 30, tzinfo=timezone.utc),
            value_exc_vat=7.78,
            value_inc_vat=8.169,
        ),
        UnitRate(
            valid_from=datetime(2023, 4, 10, 23, 30, tzinfo=timezone.utc),
            valid_to=datetime(2023, 4, 11, 0, 0, tzinfo=timezone.utc),
            value_exc_vat=15.84,
            value_inc_vat=16.632,
        ),
    ]


@responses.activate()
def test_get_unit_rates_fails_when_paginated():
    url = (
        API_BASE_URL
        + "/products/PRODUCT-CODE/electricity-tariffs/TARIFF-CODE/standard-unit-rates/"
    )

    responses.get(
        url,
        json={
            "count": 2,
            "next": url + "?page=2",
            "previous": None,
            "results": [],
        },
    )

    with pytest.raises(NotImplementedError):
        next(
            get_unit_rates(
                Tariff(code="TARIFF-CODE", product_code="PRODUCT-CODE"),
                date_from=date.today(),
                date_to=date.today() + timedelta(days=1),
            )
        )
