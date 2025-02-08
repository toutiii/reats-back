import json
import os

import boto3
from botocore.exceptions import ClientError


def fetch_aws_secrets(secret_name: str):
    region = os.getenv("AWS_REGION")

    if not region:
        raise ValueError("AWS_REGION environment variable is not set")

    secrets_client = boto3.client("secretsmanager", region_name=region)

    try:
        secrets_response = secrets_client.get_secret_value(SecretId=secret_name)
        if "SecretString" in secrets_response:
            return json.loads(secrets_response["SecretString"])  # Assume it's JSON
        return secrets_response[
            "SecretBinary"
        ]  # If stored in binary format (rare case)

    except ClientError as e:
        print(f"Error retrieving secret {secret_name}: {e}")
        return None
