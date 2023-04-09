from dataclasses import dataclass

import jq
import requests

API_BASE_URL = "https://api.octopus.energy/v1"


@dataclass
class Product:
    code: str


@dataclass
class Tariff:
    code: str


def list_products():
    response = requests.get(API_BASE_URL + "/products/")
    decoded_response = response.json()
    if decoded_response.get("next"):
        raise NotImplementedError("paginated response")

    return [
        Product(**product)
        for product in (
            jq.compile(
                '.results [] | select((.code | startswith("AGILE")) and .brand == "OCTOPUS_ENERGY" and .direction == "IMPORT") | {code: .code}'
            )
            .input(decoded_response)
            .all()
        )
    ]


def get_tariffs(product):
    response = requests.get(API_BASE_URL + "/products/" + product.code)
    decoded_response = response.json()
    return [
        Tariff(**tariff)
        for tariff in (
            jq.compile(
                ".single_register_electricity_tariffs[] | {code: .direct_debit_monthly.code}"
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

    print(tariffs)
