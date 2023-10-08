import os

import boto3
from botocore.exceptions import ClientError
from django.core.files.uploadedfile import InMemoryUploadedFile

session = boto3.session.Session(region_name=os.getenv("AWS_REGION"))
s3 = session.client("s3", config=boto3.session.Config(signature_version="s3v4"))


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
