import json
import logging

import phonenumbers
from django.conf import settings
from rest_framework import status
from rest_framework.renderers import JSONRenderer
from utils.common import get_pre_signed_url

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
            data = json.loads(json.dumps(data))
            items_values = [item["items"] for item in data]
            flattened_items = [item for sublist in items_values for item in sublist]

            for item in flattened_items:
                try:
                    item["dish"]["photo"] = get_pre_signed_url(item["dish"]["photo"])
                except KeyError as err:
                    logger.error(err)

                try:
                    item["drink"]["photo"] = get_pre_signed_url(item["drink"]["photo"])
                except KeyError as err:
                    logger.error(err)

            if flattened_items:
                response = {
                    "ok": True,
                    "status_code": status.HTTP_200_OK,
                    "data": flattened_items,
                }
            else:
                response = {
                    "ok": False,
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "data": [],
                }
        logger.info(response)
        return super().render(response)


class OrderHistoryCustomRendererWithData(JSONRenderer):
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
            data = json.loads(json.dumps(data))

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

            if data:
                response = {
                    "ok": True,
                    "status_code": status.HTTP_200_OK,
                    "data": data,
                }
            else:
                response = {
                    "ok": False,
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "data": [],
                }
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
