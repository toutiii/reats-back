import os

from django.db import connection
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    authentication_classes = []  # No auth required
    permission_classes = []  # No permissions required

    def get(self, request):
        # Check database connection
        db_host = os.environ.get("RDS_HOST") or os.environ.get("DB_HOST")
        db_status = f"Healthy db connection to {db_host}"
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")  # Simple query to check DB
        except Exception:
            db_status = "Unhealthy"

        return Response(
            {
                "status": f"Everything seems fine on {os.environ['ENV']}",
                "database": db_status,
            },
            status=200,
        )
