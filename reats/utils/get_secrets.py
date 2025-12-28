import base64
import json
import os

import boto3
from botocore.exceptions import ClientError


def fetch_aws_secrets(secret_name: str, is_json: bool = True):
    region = os.getenv("AWS_REGION")
    if not region:
        raise ValueError("AWS_REGION environment variable is not set")

    if os.environ.get("ENV") == "local":
        session = boto3.Session(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=region,
        )
    else:
        session = boto3.Session()  # Uses IAM Role in AWS

    secrets_client = session.client("secretsmanager", region_name=region)

    try:
        secrets_response = secrets_client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        print(f"Error retrieving secret {secret_name}: {e}")
        return None

    # Most common case: SecretString
    if "SecretString" in secrets_response:
        secret_str = secrets_response["SecretString"]
        if is_json:
            try:
                return json.loads(secret_str)
            except json.JSONDecodeError:
                print(f"Secret {secret_name} is not valid JSON")
                return None
        return secret_str  # <-- plaintext secret

    # Less common: SecretBinary
    if "SecretBinary" in secrets_response:
        secret_bytes = base64.b64decode(secrets_response["SecretBinary"])
        if is_json:
            try:
                return json.loads(secret_bytes.decode("utf-8"))
            except Exception:
                print(f"Secret {secret_name} binary value is not valid JSON")
                return None
        return secret_bytes

    print(f"Secret {secret_name} had no SecretString or SecretBinary")
    return None
