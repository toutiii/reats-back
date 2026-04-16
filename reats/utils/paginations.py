from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from utils.enums import SuccessMessageEnum


class StandardizedResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_page_size(self, request):
        try:
            size = int(request.query_params.get(self.page_size_query_param, self.page_size))
            return min(size, self.max_page_size)
        except (KeyError, ValueError):
            return self.page_size

    def get_paginated_response(self, results, sumary_data=None):  # ty: ignore[invalid-method-override]
        assert self.page is not None
        pagination: dict = {
            "current_page": self.page.number,
            "total_pages": self.page.paginator.num_pages,
            "total_items": self.page.paginator.count,
            "items_per_page": self.get_page_size(self.request),
        }

        data: dict = {
            "results": results,
            "pagination": pagination,
        }

        if sumary_data is not None:
            data["summary"] = sumary_data

        return Response(
            {
                "success": True,
                "message": SuccessMessageEnum.OPERATION_SUCCESSFUL,
                "data": data,
            }
        )
