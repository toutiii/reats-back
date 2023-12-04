import os
import random
import string

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile

session = boto3.session.Session(region_name=os.getenv("AWS_REGION"))
s3 = session.client("s3", config=boto3.session.Config(signature_version="s3v4"))
cognito_client = session.client("cognito-idp")


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


def generate_random_otp() -> str:
    otp = "".join(
        random.choice(string.ascii_uppercase + string.digits)
        for _ in range(settings.COOKER_POOL_OTP_LENGTH - 1)
    )
    random_symbol = random.choice(["*", "_", "-", "$", "@", "+"])
    return otp + random_symbol


def add_user_to_cognito_pool(data: dict) -> None:
    try:
        cognito_client.admin_create_user(
            UserPoolId=os.getenv("AWS_COOKER_POOL_ID"),
            Username=data.get("phone"),
            UserAttributes=[
                {"Name": "given_name", "Value": data.get("firstname")},
                {"Name": "family_name", "Value": data.get("lastname")},
            ],
            TemporaryPassword=generate_random_otp(),
            DesiredDeliveryMediums=["SMS"],
        )
    except ClientError as err:
        print(err)
