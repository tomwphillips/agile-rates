from datetime import date, datetime, timedelta, timezone

import pytest
import responses

from agile import (API_BASE_URL, Product, Tariff, UnitRate, get_products,
                   get_tariffs, get_unit_rates)


def mock_products_endpoint_factory(results, current_page=1, total_pages=1):
    url = API_BASE_URL + "/products/"

    if current_page < total_pages:
        next_url = url + f"?page={current_page + 1}"
    else:
        next_url = None

    params = {} if current_page == 1 else {"page": current_page}

    return responses.Response(
        method="GET",
        url=url,
        json={
            "next": next_url,
            "results": results,
        },
        match=[responses.matchers.query_param_matcher(params)],
    )


def mock_tariffs_endpoint_factory(product_code):
    return responses.Response(
        method="GET",
        url=API_BASE_URL + f"/products/{product_code}",
        json={
            "code": product_code,
            "single_register_electricity_tariffs": {
                "_A": {"direct_debit_monthly": {"code": f"{product_code}-A"}},
                "_B": {"direct_debit_monthly": {"code": f"{product_code}-B"}},
            },
        },
    )


def mock_unit_rates_endpoint_factory(product_code, tariff_code):
    return responses.Response(
        method="GET",
        url=API_BASE_URL
        + f"/products/{product_code}/electricity-tariffs/{tariff_code}/standard-unit-rates/",
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


@pytest.fixture
def mocked_responses():
    with responses.RequestsMock() as mock:
        yield mock


def test_get_products_only_returns_octopus_agile_tariffs(mocked_responses):
    mocked_responses.add(
        mock_products_endpoint_factory(
            [
                {"code": "AGILE-1", "brand": "OCTOPUS_ENERGY", "direction": "IMPORT"},
                {"code": "AGILE-2", "brand": "STARFISH_ENERGY", "direction": "IMPORT"},
            ]
        )
    )

    assert list(get_products()) == [Product(code="AGILE-1")]


def test_get_tariffs(mocked_responses):
    mocked_responses.add(
        mock_tariffs_endpoint_factory("AGILE-1"),
    )

    assert list(get_tariffs(Product(code="AGILE-1"))) == [
        Tariff(code="AGILE-1-A", product_code="AGILE-1"),
        Tariff(code="AGILE-1-B", product_code="AGILE-1"),
    ]


def test_get_unit_rates(mocked_responses):
    mocked_responses.add(
        mock_unit_rates_endpoint_factory("AGILE-1", "AGILE-1-A"),
    )

    got = list(
        get_unit_rates(
            Tariff(code="AGILE-1-A", product_code="AGILE-1"),
            date_from=date(2023, 4, 10),
            date_to=date(2023, 4, 11),
        )
    )
    want = [
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
    assert got == want


def test_get_unit_rates_fails_when_paginated(mocked_responses):
    product_code = "AGILE-1"
    tariff_code = "AGILE-1-A"

    url = (
        API_BASE_URL
        + f"/products/{product_code}/electricity-tariffs/{tariff_code}/standard-unit-rates/"
    )

    mocked_responses.get(
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
                Tariff(code=tariff_code, product_code=product_code),
                date_from=date.today(),
                date_to=date.today() + timedelta(days=1),
            )
        )
