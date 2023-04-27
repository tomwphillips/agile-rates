from datetime import date, datetime, time, timedelta, timezone

import pytest
import responses
from sqlalchemy import create_engine, func, select

from agile import (API_BASE_URL, Product, Tariff, UnitRate, get_products,
                   get_tariffs, get_unit_rates, metadata, parse_args,
                   product_table, tariff_table, unit_rate_table, update_all)


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


def mock_tariffs_endpoint_factory(product_code, tariff_suffixes):
    return responses.Response(
        method="GET",
        url=API_BASE_URL + f"/products/{product_code}",
        json={
            "code": product_code,
            "single_register_electricity_tariffs": {
                f"_{suffix}": {
                    "direct_debit_monthly": {"code": f"{product_code}-{suffix}"}
                }
                for suffix in tariff_suffixes
            },
        },
    )


def mock_unit_rates_endpoint_factory(product_code, tariff_code, period_from, period_to):
    def unit_periods(start, end):
        while start < end:
            yield start, start + timedelta(minutes=30)
            start += timedelta(minutes=30)

    results = [
        {
            "value_exc_vat": 1.0,
            "value_inc_vat": 1.0,
            "valid_from": start.isoformat().replace("+00:00", "Z"),
            "valid_to": end.isoformat().replace("+00:00", "Z"),
        }
        for start, end in unit_periods(period_from, period_to)
    ]

    return responses.Response(
        method="GET",
        url=API_BASE_URL
        + f"/products/{product_code}/electricity-tariffs/{tariff_code}/standard-unit-rates/",
        json={"count": 2, "next": None, "previous": None, "results": results},
        match=[
            responses.matchers.query_param_matcher(
                {
                    "period_from": period_from.isoformat().replace("+00:00", "Z"),
                    "period_to": period_to.isoformat().replace("+00:00", "Z"),
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
        mock_tariffs_endpoint_factory("AGILE-1", ["A", "B"]),
    )

    assert list(get_tariffs(Product(code="AGILE-1"))) == [
        Tariff(code="AGILE-1-A", product_code="AGILE-1"),
        Tariff(code="AGILE-1-B", product_code="AGILE-1"),
    ]


def test_get_unit_rates(mocked_responses):
    date_from = date(2023, 4, 10)
    date_to = date(2023, 4, 11)

    mocked_responses.add(
        mock_unit_rates_endpoint_factory(
            "AGILE-1",
            "AGILE-1-A",
            datetime.combine(date_from, time(), timezone.utc),
            datetime.combine(date_to, time(), timezone.utc),
        ),
    )

    got = list(
        get_unit_rates(
            Tariff(code="AGILE-1-A", product_code="AGILE-1"),
            date_from,
            date_to,
        )
    )
    assert got[0] == UnitRate(
        valid_from=datetime.combine(date_from, time(0, 0), timezone.utc),
        valid_to=datetime.combine(date_from, time(0, 30), timezone.utc),
        value_exc_vat=1.0,
        value_inc_vat=1.0,
        tariff_code="AGILE-1-A",
    )
    assert len(got) == 48


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


@pytest.fixture
def engine():
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    return engine


def test_update_all_is_idempotent_when_responses_are_unchanged(
    mocked_responses, engine
):
    product_code = "AGILE-1"
    tariff_code = "AGILE-1-A"
    unit_rate_from = datetime.combine(datetime.today(), time(), timezone.utc)
    unit_rate_to = unit_rate_from + timedelta(days=1)

    mocked_responses.add(
        mock_products_endpoint_factory(
            [{"code": product_code, "brand": "OCTOPUS_ENERGY", "direction": "IMPORT"}]
        )
    )
    mocked_responses.add(
        mock_tariffs_endpoint_factory(product_code, (tariff_code[-1],))
    )
    mocked_responses.add(
        mock_unit_rates_endpoint_factory(
            product_code, tariff_code, unit_rate_from, unit_rate_to
        )
    )

    def make_assertions(engine):
        with engine.connect() as conn:
            assert conn.execute(
                select(product_table).where(product_table.c.code == product_code)
            ).one()
            assert conn.execute(
                select(tariff_table).where(tariff_table.c.product_code == product_code)
            ).one()
            assert conn.scalar(select(func.count()).select_from(unit_rate_table)) == 48

    update_all(engine, unit_rate_from, unit_rate_to)
    make_assertions(engine)

    update_all(engine, unit_rate_from, unit_rate_to)
    make_assertions(engine)


def test_parse_args():
    tests = [
        (
            [],
            {
                "database_url": "sqlite:///agile.db",
                "unit_rate_from": date.today(),
                "unit_rate_to": (date.today() + timedelta(days=1)),
            },
        ),
        (
            ["--database-url", "sqlite:///test.db"],
            {
                "database_url": "sqlite:///test.db",
                "unit_rate_from": date.today(),
                "unit_rate_to": date.today() + timedelta(days=1),
            },
        ),
        (
            ["--unit-rate-from", "2023-01-01", "--unit-rate-to", "2023-01-31"],
            {
                "database_url": "sqlite:///agile.db",
                "unit_rate_from": date(2023, 1, 1),
                "unit_rate_to": date(2023, 1, 31),
            },
        ),
    ]

    for args, expected in tests:
        assert vars(parse_args(args)) == expected
