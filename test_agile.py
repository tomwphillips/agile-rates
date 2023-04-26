from datetime import date, datetime, timedelta, timezone

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


@pytest.fixture
def mock_api():
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock_api:
        products_url = API_BASE_URL + "/products/"

        mock_api.get(
            products_url,
            json={
                "next": products_url + "?page=2",
                "results": [
                    {"code": "AGILE-2", "brand": "STARFISH_ENERGY"},
                    {"code": "STIFF-1", "brand": "OCTOPUS_ENERGY"},
                ],
            },
            match=[responses.matchers.query_param_matcher({})],
        )

        mock_api.get(
            products_url,
            json={
                "next": None,
                "results": [
                    {
                        "code": "AGILE-1",
                        "brand": "OCTOPUS_ENERGY",
                        "direction": "IMPORT",
                    },
                ],
            },
            match=[responses.matchers.query_param_matcher({"page": 2})],
        )

        mock_api.get(
            API_BASE_URL + "/products/AGILE-1",
            json={
                "code": "PRODUCT-1",
                "single_register_electricity_tariffs": {
                    "_A": {"direct_debit_monthly": {"code": "AGILE-1-A"}},
                    "_B": {"direct_debit_monthly": {"code": "AGILE-1-B"}},
                },
            },
        )

        mock_api.get(
            API_BASE_URL
            + "/products/AGILE-1/electricity-tariffs/AGILE-1-A/standard-unit-rates/",
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

        yield mock_api


def test_list_products(mock_api):
    products = list(list_products())
    assert products == [Product(code="AGILE-1")]


def test_get_tariffs(mock_api):
    tariffs = get_tariffs(Product(code="AGILE-1"))
    assert tariffs == [
        Tariff(code="AGILE-1-A", product_code="AGILE-1"),
        Tariff(code="AGILE-1-B", product_code="AGILE-1"),
    ]


def test_get_unit_rates(mock_api):
    unit_rates = list(
        get_unit_rates(
            Tariff(code="AGILE-1-A", product_code="AGILE-1"),
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
            tariff_code="AGILE-1-A",
        ),
        UnitRate(
            valid_from=datetime(2023, 4, 10, 23, 30, tzinfo=timezone.utc),
            valid_to=datetime(2023, 4, 11, 0, 0, tzinfo=timezone.utc),
            value_exc_vat=15.84,
            value_inc_vat=16.632,
            tariff_code="AGILE-1-A",
        ),
    ]


@responses.activate()
def test_get_unit_rates_fails_when_paginated():
    url = (
        API_BASE_URL
        + "/products/AGILE-1/electricity-tariffs/AGILE-1-A/standard-unit-rates/"
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
                Tariff(code="AGILE-1-A", product_code="AGILE-1"),
                date_from=date.today(),
                date_to=date.today() + timedelta(days=1),
            )
        )
