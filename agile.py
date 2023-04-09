import marshmallow
import requests

API_BASE_URL = "https://api.octopus.energy/v1"


class ProductSchema(marshmallow.Schema):
    code = marshmallow.fields.String()


def list_products():
    response = requests.get(API_BASE_URL + "/products/")
    decoded_response = response.json()
    if decoded_response.get("next"):
        raise NotImplementedError("paginated response")

    return ProductSchema(many=True, unknown=marshmallow.EXCLUDE).load(
        decoded_response["results"]
    )
