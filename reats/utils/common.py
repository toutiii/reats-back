import os

import boto3
from botocore.exceptions import ClientError
from django.core.files.uploadedfile import InMemoryUploadedFile

s3 = boto3.client("s3")


def upload_image_to_s3(image: InMemoryUploadedFile, image_path: str) -> str:
    try:
        s3.upload_fileobj(
            image,
            os.getenv("AWS_S3_BUCKET"),
            image_path,
        )
    except ClientError as err:
        print(err)

    image_base_url = f"https://{os.getenv('AWS_S3_BUCKET')}.s3.{os.getenv('AWS_REGION')}.amazonaws.com"

    return image_base_url + "/" + image_path
