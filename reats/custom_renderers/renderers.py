import json
import logging

import phonenumbers
from cooker_app.models import CookerModel
from customer_app.models import CustomerModel
from django.conf import settings
from rest_framework import status
from rest_framework.renderers import JSONRenderer
from utils.common import create_stripe_ephemeral_key, get_pre_signed_url
from utils.enums import OrderStatusEnum

logger = logging.getLogger("watchtower-logger")


class CookerCustomRendererWithData(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        try:
            data["detail"].code
        except KeyError:
            status_code = status.HTTP_200_OK
        except Exception as err:
            logger.error(err)
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
                            "photo": get_pre_signed_url(data["photo"]),
                            "siret": data["siret"],
                            "firstname": data["firstname"],
                            "lastname": data["lastname"],
                            "phone": phonenumbers.format_number(
                                phonenumbers.parse(
                                    data["phone"], settings.PHONE_REGION
                                ),
                                phonenumbers.PhoneNumberFormat.NATIONAL,
                            ).replace(" ", ""),
                            "max_order_number": str(data["max_order_number"]),
                            "is_online": data["is_online"],
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

        if status_code == status.HTTP_401_UNAUTHORIZED:
            try:
                response["error_code"] = data["detail"].code
            except KeyError:
                pass

        logger.info(response)
        return super().render(response)


class CustomerCustomRendererWithData(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        try:
            data["detail"].code
        except KeyError:
            status_code = status.HTTP_200_OK
        except Exception as err:
            logger.error(err)
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
                            "photo": get_pre_signed_url(data["photo"]),
                            "firstname": data["firstname"],
                            "lastname": data["lastname"],
                            "phone": phonenumbers.format_number(
                                phonenumbers.parse(
                                    data["phone"], settings.PHONE_REGION
                                ),
                                phonenumbers.PhoneNumberFormat.NATIONAL,
                            ).replace(" ", ""),
                        },
                    },
                },
            }
        else:
            response = {
                "ok": False,
                "status_code": status_code,
            }

        if status_code == status.HTTP_401_UNAUTHORIZED:
            try:
                response["error_code"] = data["detail"].code
            except KeyError:
                pass

        logger.info(response)
        return super().render(response)


class DeliverCustomRendererWithData(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        try:
            data["detail"].code
        except KeyError:
            status_code = status.HTTP_200_OK
        except Exception as err:
            logger.error(err)
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
                            "photo": get_pre_signed_url(data["photo"]),
                            "firstname": data["firstname"],
                            "lastname": data["lastname"],
                            "delivery_vehicle": data["delivery_vehicle"],
                            "town": data["town"],
                            "delivery_radius": data["delivery_radius"],
                            "siret": data["siret"],
                            "phone": phonenumbers.format_number(
                                phonenumbers.parse(
                                    data["phone"], settings.PHONE_REGION
                                ),
                                phonenumbers.PhoneNumberFormat.NATIONAL,
                            ).replace(" ", ""),
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
        logger.info(data)
        status_code = renderer_context["response"].status_code
        response = {
            "ok": True,
            "status_code": status_code,
        }

        if not data and status_code == status.HTTP_200_OK:
            response = {
                "ok": True,
                "status_code": status.HTTP_404_NOT_FOUND,
            }

        if data and status_code == status.HTTP_200_OK:
            response.update(
                {
                    "data": [
                        {
                            k: (
                                get_pre_signed_url(v)
                                if k == "photo"
                                else (str(v) if not isinstance(v, bool) else v)
                            )
                            for k, v in item.items()
                        }
                        for item in data
                    ],
                }
            )

        if not str(status_code).startswith("2"):
            response = {
                "ok": False,
                "status_code": status_code,
            }

        if status_code == status.HTTP_401_UNAUTHORIZED:
            try:
                response["error_code"] = data["detail"].code
            except KeyError:
                pass

        logger.info(response)
        return super().render(response)


class DishesCountriesCustomRendererWithData(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        logger.info(data)
        status_code = renderer_context["response"].status_code
        response = {
            "ok": True,
            "status_code": status_code,
        }

        if not data and status_code == status.HTTP_200_OK:
            response = {
                "ok": True,
                "status_code": status.HTTP_404_NOT_FOUND,
            }

        if data and status_code == status.HTTP_200_OK:
            response.update({"data": [item["country"] for item in data]})

        if not str(status_code).startswith("2"):
            response = {
                "ok": False,
                "status_code": status_code,
            }

        if status_code == status.HTTP_401_UNAUTHORIZED:
            try:
                response["error_code"] = data["detail"].code
            except KeyError:
                pass

        logger.info(response)
        return super().render(response)


class CustomRendererWithoutData(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        logger.info(data)
        status_code = renderer_context["response"].status_code
        response = {
            "ok": True,
            "status_code": status_code,
        }

        if data and status_code == status.HTTP_200_OK:
            if "token" in data:
                response["token"] = data["token"]

            if "user_id" in data:
                response["user_id"] = data["user_id"]

            if "access" in data:
                response["access"] = data["access"]

        if not str(status_code).startswith("2"):
            response["ok"] = False

        if status_code == status.HTTP_401_UNAUTHORIZED:
            try:
                response["error_code"] = data["detail"].code
            except KeyError:
                pass

        return super().render(response)


class AddressCustomRendererWithData(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        status_code = renderer_context["response"].status_code

        response = {
            "ok": True,
            "status_code": status_code,
        }

        if status_code == status.HTTP_401_UNAUTHORIZED:
            try:
                response["error_code"] = data["detail"].code
            except KeyError:
                pass

        if not str(status_code).startswith("2"):
            response["ok"] = False

        if status_code == status.HTTP_200_OK:
            if data:
                response = {
                    "ok": True,
                    "status_code": status.HTTP_200_OK,
                    "data": json.loads(json.dumps(data)),
                }
            else:
                response = {
                    "ok": False,
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "data": [],
                }
        logger.info(response)
        return super().render(response)


class OrderCustomRendererWithData(JSONRenderer):
    def _enrich_response(self, response: dict) -> None:
        """
        Order for history records does not have customer in serializer
        """
        if "customer" in response:
            try:
                customer: CustomerModel = CustomerModel.objects.get(
                    id=response["customer"]["id"]
                )
            except TypeError as err:
                logger.error(err)
                customer = CustomerModel.objects.get(id=response["customer"])
            response["customer"] = {
                "id": customer.id,
                "stripe_id": customer.stripe_id,
                "lastname": customer.lastname,
                "firstname": customer.firstname,
            }

        order_status = response.get("status")

        if order_status is None or order_status == OrderStatusEnum.DRAFT:
            response["ephemeral_key"] = create_stripe_ephemeral_key(customer)

        if "cooker" in response:
            cooker: CookerModel = CookerModel.objects.get(id=response["cooker"])
            response["cooker"] = {
                "id": cooker.id,
                "firstname": cooker.firstname,
                "lastname": cooker.lastname,
            }

    def render(self, data, accepted_media_type=None, renderer_context=None):
        status_code = renderer_context["response"].status_code
        response = {
            "ok": True,
            "status_code": status_code,
        }
        if not str(status_code).startswith("2"):
            response["ok"] = False

        if status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK):
            data = json.loads(json.dumps(data))
            if isinstance(data, list):
                for order_item in data:
                    for item in order_item["items"]:
                        try:
                            item["dish"]["photo"] = get_pre_signed_url(
                                item["dish"]["photo"]
                            )
                        except KeyError as err:
                            logger.error(err)

                        try:
                            item["drink"]["photo"] = get_pre_signed_url(
                                item["drink"]["photo"]
                            )
                        except KeyError as err:
                            logger.error(err)
                response = {
                    "ok": True,
                    "status_code": status.HTTP_200_OK,
                    "data": data if data else [],
                }
                for response_item in response["data"]:
                    self._enrich_response(response_item)

            else:
                response = {
                    "ok": True,
                    "status_code": status.HTTP_200_OK,
                    "data": data,
                }
                self._enrich_response(response["data"])

        if status_code == status.HTTP_401_UNAUTHORIZED:
            try:
                response["error_code"] = data["detail"].code
            except KeyError:
                pass

        logger.info(response)
        return super().render(response)


class DeliveryStatsCustomRendererWithData(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        status_code = renderer_context["response"].status_code

        response = {
            "ok": True,
            "status_code": status_code,
        }

        if status_code == status.HTTP_401_UNAUTHORIZED:
            try:
                response["error_code"] = data["detail"].code
            except KeyError:
                pass

        if not str(status_code).startswith("2"):
            response["ok"] = False

        if status_code == status.HTTP_200_OK:
            if data and data.get("data"):
                response = {
                    "ok": True,
                    "status_code": status.HTTP_200_OK,
                    "data": data["data"],
                }
            else:
                response = {
                    "ok": False,
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "data": [],
                }
        logger.info(response)
        return super().render(response)


class CustomJSONRendererWithData(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        logger.info(data)
        status_code = renderer_context["response"].status_code

        if status_code == status.HTTP_200_OK:
            response = data

        if status_code == status.HTTP_401_UNAUTHORIZED:
            response = {
                "ok": False,
                "status_code": status_code,
            }
            try:
                response["error_code"] = data["detail"].code
            except KeyError:
                pass

        logger.info(response)
        return super().render(response)
