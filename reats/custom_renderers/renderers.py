from rest_framework.renderers import JSONRenderer


class CustomRendererWithData(JSONRenderer):
    def __init__(self, send_response_data: bool = True, *args, **kwargs) -> None:
        self._send_response_data = send_response_data
        super().__init__(*args, **kwargs)

    def render(self, data, accepted_media_type=None, renderer_context=None):
        status_code = renderer_context["response"].status_code
        response = {
            "ok": True,
            "status_code": status_code,
        }

        if not str(status_code).startswith("2"):
            response["ok"] = False
            response["status_code"] = status_code

        if self._send_response_data:
            try:
                response["response_data"] = data["detail"]
            except KeyError:
                response["response_data"] = data

        return super(CustomRendererWithData, self).render(
            response, accepted_media_type, renderer_context
        )


class CustomRendererWithoutData(CustomRendererWithData):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(False, *args, **kwargs)
