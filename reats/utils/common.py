import hashlib
import os
import random
import string

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile

session = boto3.session.Session(region_name=os.getenv("AWS_REGION"))
s3 = session.client("s3", config=boto3.session.Config(signature_version="s3v4"))
pinpoint_client = boto3.client("pinpoint", region_name=os.getenv("AWS_REGION"))


def upload_image_to_s3(image: InMemoryUploadedFile, image_path: str) -> None:
    try:
        s3.upload_fileobj(
            image,
            os.getenv("AWS_S3_BUCKET"),
            image_path,
        )
    except ClientError as err:
        print(err)
    else:
        print(f"{image_path} has been uploaded to S3.")


def get_pre_signed_url(key: str) -> str:
    try:
        url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": os.getenv("AWS_S3_BUCKET"),
                "Key": key,
            },
        )
    except ClientError as err:
        print(err)
    else:
        print(url)

    return url


def delete_s3_object(key: str) -> None:
    try:
        s3.delete_object(Bucket=os.getenv("AWS_S3_BUCKET"), Key=key)
    except ClientError as err:
        print(err)
    else:
        print(f"{key} has been removed from {os.getenv('AWS_S3_BUCKET')} bucket")


def generate_ref_id(data: dict):
    reference_id = data["phone"] + data["firstname"] + data["lastname"]
    return hashlib.md5(reference_id.encode()).hexdigest()


def send_otp(data: dict) -> None:
    try:
        response = pinpoint_client.send_otp_message(
            ApplicationId=os.getenv("AWS_PINPOINT_APP_ID"),
            SendOTPMessageRequestParameters={
                "Channel": os.getenv("AWS_PINPOINT_CHANNEL"),
                "BrandName": os.getenv("AWS_PINPOINT_BRAND_NAME"),
                "CodeLength": int(os.getenv("AWS_PINPOINT_CODE_LENGTH", "6")),
                "ValidityPeriod": int(os.getenv("AWS_PINPOINT_VALIDITY_PERIOD", "10")),
                "AllowedAttempts": int(os.getenv("AWS_PINPOINT_ALLOWED_ATTEMPTS", "3")),
                "Language": os.getenv("AWS_PINPOINT_LANGUAGE"),
                "OriginationIdentity": os.getenv("AWS_SENDER_ID"),
                "DestinationIdentity": data["phone"],
                "ReferenceId": generate_ref_id(data),
            },
        )

    except ClientError as e:
        print(e.response)
    else:
        print(response)
