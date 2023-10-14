from rest_framework import status
from rest_framework.renderers import JSONRenderer
from utils.common import get_pre_signed_url


class CookerCustomRendererWithData(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        try:
            data["detail"].code
        except KeyError:
            status_code = status.HTTP_200_OK
        except Exception as err:
            print(err)
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        else:
            status_code = status.HTTP_404_NOT_FOUND

        if status_code == status.HTTP_200_OK:
            response = {
                "ok": True,
                "status_code": status_code,
                "data": {
                    "personal_infos_section": {
                        "title": "personal_infos",
                        "data": {
                            "photo": "https://img-3.journaldesfemmes.fr/M_bbWpTVNekL5O_MLzQ4dyInmJU=/750x/smart/1c9fe4d4419047f18efc37134a046e5a/recipe-jdf/1001383.jpg",  # noqa
                            "siret": data["siret"],
                            "firstname": data["firstname"],
                            "lastname": data["lastname"],
                            "phone": data["phone"],
                            "max_order_number": "7",
                        },
                    },
                    "address_section": {
                        "title": "address",
                        "data": {
                            "street_number": data["street_number"],
                            "street_name": data["street_name"],
                            "address_complement": data["address_complement"],
                            "postal_code": data["postal_code"],
                            "town": data["town"],
                        },
                    },
                },
            }
        else:
            response = {
                "ok": False,
                "status_code": status_code,
            }

        return super().render(response)


class CustomRendererWithData(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        if not data:
            response = {
                "ok": True,
                "status_code": status.HTTP_404_NOT_FOUND,
            }
        else:
            response = {
                "ok": True,
                "status_code": status.HTTP_200_OK,
                "data": [
                    {
                        k: get_pre_signed_url(v)
                        if k == "photo"
                        else (str(v) if type(v) != bool else v)
                        for k, v in item.items()
                    }
                    for item in data
                ],
            }

        print(response)
        return super().render(response)


class CustomRendererWithoutData(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        status_code = renderer_context["response"].status_code
        response = {
            "ok": True,
            "status_code": status_code,
        }

        if not str(status_code).startswith("2"):
            response["ok"] = False

        return super().render(response)
