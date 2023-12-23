import hashlib
import os
from typing import Type, Union

import boto3
import phonenumbers
from botocore.exceptions import ClientError
from cooker_app.models import CookerModel
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


def format_phone(phone: str) -> str:
    return phonenumbers.format_number(
        phonenumbers.parse(
            phone,
            settings.PHONE_REGION,
        ),
        phonenumbers.PhoneNumberFormat.E164,
    )


def generate_ref_id(phone: str):
    return hashlib.md5(phone.encode()).hexdigest()


def send_otp(phone: str) -> Union[dict, None]:
    try:
        response: dict = pinpoint_client.send_otp_message(
            ApplicationId=os.getenv("AWS_PINPOINT_APP_ID"),
            SendOTPMessageRequestParameters={
                "Channel": os.getenv("AWS_PINPOINT_CHANNEL"),
                "BrandName": os.getenv("AWS_PINPOINT_BRAND_NAME"),
                "CodeLength": int(os.getenv("AWS_PINPOINT_CODE_LENGTH", "6")),
                "ValidityPeriod": int(os.getenv("AWS_PINPOINT_VALIDITY_PERIOD", "10")),
                "AllowedAttempts": int(os.getenv("AWS_PINPOINT_ALLOWED_ATTEMPTS", "3")),
                "Language": os.getenv("AWS_PINPOINT_LANGUAGE"),
                "OriginationIdentity": os.getenv("AWS_SENDER_ID"),
                "DestinationIdentity": phone,
                "ReferenceId": generate_ref_id(phone),
            },
        )

    except ClientError as e:
        print(e.response)
        return None

    return response


def is_otp_valid(data: dict) -> bool:
    try:
        response = pinpoint_client.verify_otp_message(
            ApplicationId=os.getenv("AWS_PINPOINT_APP_ID"),
            VerifyOTPMessageRequestParameters={
                "DestinationIdentity": format_phone(data["phone"]),
                "ReferenceId": generate_ref_id(format_phone(data["phone"])),
                "Otp": data["otp"],
            },
        )

    except ClientError as e:
        print(e.response)
        return False

    return response["VerificationResponse"]["Valid"]


def activate_user(model: Type[CookerModel], data: dict) -> None:
    user = model.objects.get(phone=format_phone(data["phone"]))
    user.is_activated = True
    user.save()
