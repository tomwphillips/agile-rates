import argparse
import dataclasses
import datetime as dt

import jq
import requests
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.dialects.sqlite import insert

API_BASE_URL = "https://api.octopus.energy/v1"


metadata = MetaData()

product_table = Table(
    "products",
    metadata,
    Column("code", String, primary_key=True),
)

tariff_table = Table(
    "tariffs",
    metadata,
    Column("code", String, primary_key=True),
    Column("product_code", String, ForeignKey("products.code")),
)

unit_rate_table = Table(
    "unit_rates",
    metadata,
    Column("tariff_code", String, ForeignKey("tariffs.code")),
    Column("valid_from", DateTime),
    Column("valid_to", DateTime),
    Column("value_exc_vat", Float),
    Column("value_inc_vat", Float),
    UniqueConstraint(
        "tariff_code",
        "valid_from",
        "valid_to",
    ),
)


@dataclasses.dataclass
class Product:
    code: str


@dataclasses.dataclass
class Tariff:
    code: str
    product_code: str


@dataclasses.dataclass
class UnitRate:
    tariff_code: str
    valid_from: dt.datetime
    valid_to: dt.datetime
    value_exc_vat: float
    value_inc_vat: float

    def from_decoded_json(**kwargs):
        return UnitRate(
            tariff_code=kwargs["tariff_code"],
            valid_from=dt.datetime.fromisoformat(kwargs["valid_from"]),
            valid_to=dt.datetime.fromisoformat(kwargs["valid_to"]),
            value_exc_vat=kwargs["value_exc_vat"],
            value_inc_vat=kwargs["value_inc_vat"],
        )


def get_products():
    processor = jq.compile(
        '.results [] | select((.code | startswith("AGILE")) and .brand == "OCTOPUS_ENERGY" and .direction == "IMPORT") | {code: .code}'
    )

    url = API_BASE_URL + "/products/"
    while True:
        response = requests.get(url)
        decoded_response = response.json()

        for product in processor.input(decoded_response):
            yield Product(**product)

        if decoded_response.get("next"):
            url = decoded_response["next"]
        else:
            break


def get_tariffs(product):
    response = requests.get(API_BASE_URL + "/products/" + product.code)
    decoded_response = response.json()
    processor = jq.compile(
        ".single_register_electricity_tariffs[] | {code: .direct_debit_monthly.code}"
    )
    for tariff in processor.input(decoded_response):
        yield Tariff(**tariff, product_code=product.code)


def get_unit_rates(tariff, date_from, date_to):
    url = (
        API_BASE_URL
        + f"/products/{tariff.product_code}/electricity-tariffs/{tariff.code}/standard-unit-rates/"
    )

    response = requests.get(
        url,
        params={
            "period_from": dt.datetime.combine(
                date_from, dt.time(), dt.timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "period_to": dt.datetime.combine(
                date_to, dt.time(), dt.timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )
    decoded_response = response.json()

    if decoded_response.get("next"):
        raise NotImplementedError("Pagination not implemented")

    processor = jq.compile(
        ".results[] | {valid_from: .valid_from, valid_to: .valid_to, value_exc_vat: .value_exc_vat, value_inc_vat: .value_inc_vat}"
    )

    for unit_rate in processor.input(decoded_response):
        yield UnitRate.from_decoded_json(**unit_rate, tariff_code=tariff.code)


def update_all(engine, unit_rate_from, unit_rate_to):
    products = list(get_products())
    tarrifs = [tarrif for product in products for tarrif in get_tariffs(product)]
    unit_rates = [
        unit_rate
        for tarrif in tarrifs
        for unit_rate in get_unit_rates(tarrif, unit_rate_from, unit_rate_to)
    ]

    with engine.connect() as conn:
        conn.execute(
            insert(product_table).on_conflict_do_nothing(),
            [dataclasses.asdict(product) for product in products],
        )
        conn.execute(
            insert(tariff_table).on_conflict_do_nothing(),
            [dataclasses.asdict(tariff) for tariff in tarrifs],
        )
        conn.execute(
            insert(unit_rate_table).on_conflict_do_nothing(),
            [dataclasses.asdict(unit_rate) for unit_rate in unit_rates],
        )
        conn.commit()


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database-url",
        default="sqlite:///agile.db",
        help="SQLAlchemy database URL. Defaults to %(default)s.",
    )
    parser.add_argument(
        "--unit-rate-from",
        type=dt.date.fromisoformat,
        default=dt.date.today(),
        help="Date from which to fetch unit rates. Defaults to today.",
    )
    parser.add_argument(
        "--unit-rate-to",
        type=dt.date.fromisoformat,
        default=dt.date.today() + dt.timedelta(days=1),
        help="Date to which to fetch unit rates. Defaults to tomorrow.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    engine = create_engine(args.database_url)
    update_all(engine, args.unit_rate_from, args.unit_rate_to)
