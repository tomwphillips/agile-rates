from dataclasses import dataclass
from datetime import datetime

import jq
import requests

API_BASE_URL = "https://api.octopus.energy/v1"


@dataclass
class Product:
    code: str


@dataclass
class Tariff:
    code: str
    product_code: str


@dataclass
class UnitRate:
    valid_from: datetime
    valid_to: datetime
    value_exc_vat: float
    value_inc_vat: float

    def from_decoded_json(**kwargs):
        return UnitRate(
            valid_from=datetime.fromisoformat(kwargs["valid_from"]),
            valid_to=datetime.fromisoformat(kwargs["valid_to"]),
            value_exc_vat=kwargs["value_exc_vat"],
            value_inc_vat=kwargs["value_inc_vat"],
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


def get_unit_rates(tariff):
    response = requests.get(
        API_BASE_URL
        + f"/products/{tariff.product_code}/electricity-tariffs/{tariff.code}/standard-unit-rates/"
    )
    decoded_response = response.json()
    if decoded_response.get("next"):
        raise NotImplementedError("paginated response")

    return [
        UnitRate.from_decoded_json(**unit_rate)
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
        print(tariff)
