import datetime as dt
from typing import List

import jq
import requests
from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

API_BASE_URL = "https://api.octopus.energy/v1"


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    code: Mapped[str] = mapped_column(primary_key=True)
    tariffs: Mapped[List["Tariff"]] = relationship()

    def __eq__(self, other):
        return self.code == other.code and self.tariffs == other.tariffs

    def __repr__(self):
        return f"Product(code={self.code!r}, tariffs={self.tariffs!r})"


class Tariff(Base):
    __tablename__ = "tariffs"

    code: Mapped[str] = mapped_column(primary_key=True)
    product_code: Mapped[str] = mapped_column(ForeignKey("products.code"))

    def __eq__(self, other):
        return self.code == other.code and self.product_code == other.product_code

    def __repr__(self):
        return f"Tariff(code={self.code!r}, product_code={self.product_code!r})"


class UnitRate(Base):
    __tablename__ = "unit_rates"

    id: Mapped[int] = mapped_column(primary_key=True)
    tariff_code: Mapped[str] = mapped_column(ForeignKey("tariffs.code"))
    valid_from: Mapped[dt.datetime]
    valid_to: Mapped[dt.datetime]
    value_exc_vat: Mapped[float]
    value_inc_vat: Mapped[float]

    def from_decoded_json(**kwargs):
        return UnitRate(
            tariff_code=kwargs["tariff_code"],
            valid_from=dt.datetime.fromisoformat(kwargs["valid_from"]),
            valid_to=dt.datetime.fromisoformat(kwargs["valid_to"]),
            value_exc_vat=kwargs["value_exc_vat"],
            value_inc_vat=kwargs["value_inc_vat"],
        )

    def __eq__(self, other):
        return (
            self.tariff_code == other.tariff_code
            and self.valid_from == other.valid_from
            and self.valid_to == other.valid_to
            and self.value_exc_vat == other.value_exc_vat
            and self.value_inc_vat == other.value_inc_vat
        )

    def __repr__(self):
        return (
            f"UnitRate("
            f"tariff_code={self.tariff_code!r}, "
            f"valid_from={self.valid_from!r}, "
            f"valid_to={self.valid_to!r}, "
            f"value_exc_vat={self.value_exc_vat!r}, "
            f"value_inc_vat={self.value_inc_vat!r}"
            f")"
        )


def list_products():
    url = API_BASE_URL + "/products/"
    while True:
        response = requests.get(url)
        decoded_response = response.json()

        yield from [
            Product(**product)
            for product in (
                jq.compile(
                    '.results [] | select((.code | startswith("AGILE")) and .brand == "OCTOPUS_ENERGY" and .direction == "IMPORT") | {code: .code}'
                )
                .input(decoded_response)
                .all()
            )
        ]

        if decoded_response.get("next"):
            url = decoded_response["next"]
        else:
            break


def get_tariffs(product):
    response = requests.get(API_BASE_URL + "/products/" + product.code)
    decoded_response = response.json()
    return [
        Tariff(**tariff, product_code=product.code)
        for tariff in (
            jq.compile(
                ".single_register_electricity_tariffs[] | {code: .direct_debit_monthly.code}"
            )
            .input(decoded_response)
            .all()
        )
    ]


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

    yield from [
        UnitRate.from_decoded_json(**unit_rate, tariff_code=tariff.code)
        for unit_rate in (
            jq.compile(
                ".results[] | {valid_from: .valid_from, valid_to: .valid_to, value_exc_vat: .value_exc_vat, value_inc_vat: .value_inc_vat}"
            )
            .input(decoded_response)
            .all()
        )
    ]


if __name__ == "__main__":
    products = list_products()

    tariffs = []
    for product in products:
        tariffs.extend(get_tariffs(product))

    for tariff in tariffs:
        print("~~~~~~~", tariff, "~~~~~~~")

        unit_rates = get_unit_rates(
            tariff,
            dt.date.today() + dt.timedelta(days=1),
            dt.date.today() + dt.timedelta(days=2),
        )

        for unit_rate in unit_rates:
            print(unit_rate)
