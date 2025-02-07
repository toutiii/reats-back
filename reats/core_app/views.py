from django.db import connection
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    authentication_classes = []  # No auth required
    permission_classes = []  # No permissions required

    def get(self, request):
        # Check database connection
        db_status = "healthy"
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")  # Simple query to check DB
        except Exception:
            db_status = "unhealthy"

        return Response(
            {
                "status": "ok",
                "database": db_status,
            },
            status=200,
        )
