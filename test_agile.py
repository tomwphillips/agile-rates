import responses

from agile import API_BASE_URL, list_products


@responses.activate()
def test_list_products():
    responses.get(
        API_BASE_URL + "/products/",
        json={
            "results": [
                {"code": "PRODUCT-1", "full_name": "Product 1"},
                {"code": "PRODUCT-2", "full_name": "Product 2"},
            ]
        },
    )
    products = list_products()
    assert products == [
        {"code": "PRODUCT-1"},
        {"code": "PRODUCT-2"},
    ]
