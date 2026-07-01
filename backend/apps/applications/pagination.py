"""
Application Management System — Pagination

Custom pagination configuration for application list endpoints.
Uses DRF's PageNumberPagination with sensible defaults and
client-configurable page size.
"""

from rest_framework.pagination import PageNumberPagination


class ApplicationPagination(PageNumberPagination):
    """
    Standard pagination for application list views.

    Defaults to 20 items per page. Clients can override via the
    `page_size` query parameter, up to a maximum of 100.

    Response envelope:
        {
            "count": <total>,
            "next": <url|null>,
            "previous": <url|null>,
            "results": [...]
        }
    """

    page_size: int = 20
    page_size_query_param: str = "page_size"
    max_page_size: int = 100
