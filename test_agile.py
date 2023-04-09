import responses

from agile import API_BASE_URL, Tariff, get_tariffs, list_products, get_tariffs, Product


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
        Tariff(code="A-1"),
        Tariff(code="B-1"),
    ]
