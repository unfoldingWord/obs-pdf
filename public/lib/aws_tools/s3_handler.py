import os
import json

import boto3
from boto3.session import Session
import botocore



class S3Handler:
    def __init__(self, bucket_name=None, aws_access_key_id=None, aws_secret_access_key=None,
                 aws_region_name='us-west-2'):
        self.bucket_name = bucket_name
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_region_name = aws_region_name
        self.bucket = None
        self.client = None
        self.resource = None
        self.setup_resources()


    def setup_resources(self):
        if self.aws_access_key_id and self.aws_secret_access_key:
            session = Session(aws_access_key_id=self.aws_access_key_id,
                              aws_secret_access_key=self.aws_secret_access_key,
                              region_name=self.aws_region_name)
            self.resource = session.resource('s3')
            self.client = session.client('s3')
        else:
            self.resource = boto3.resource('s3',
                                           aws_access_key_id=self.aws_access_key_id,
                                           aws_secret_access_key=self.aws_secret_access_key,
                                           region_name=self.aws_region_name)
            self.client = boto3.client('s3',
                                       aws_access_key_id=self.aws_access_key_id,
                                       aws_secret_access_key=self.aws_secret_access_key,
                                       region_name=self.aws_region_name)

        self.bucket = None
        if self.bucket_name:
            self.bucket = self.resource.Bucket(self.bucket_name)


    def upload_file(self, path:str, key:str, cache_time=600, content_type=None):
        """
        Upload file to S3 storage. Similar to the s3.upload_file, however, that
        does not work nicely with moto, whereas this function does.
        :param string path: file to upload
        :param string key: name of the object in the bucket
        """
        from lib.general_tools.file_utils import get_mime_type
        assert 'http' not in key.lower()

        with open(path, 'rb') as f:
            binary = f.read()
        if content_type is None:
            content_type = get_mime_type(path)
        self.bucket.put_object(
            Key=key,
            Body=binary,
            ContentType=content_type,
            CacheControl=f'max-age={cache_time}'
        )


    def get_object(self, key:str):
        return self.resource.Object(bucket_name=self.bucket_name, key=key)


    def put_contents(self, key:str, body, catch_exception:bool=True):
            if catch_exception:
                try:
                    return self.get_object(key).put(Body=body)
                except:
                    return None
            else:
                return self.get_object(key).put(Body=body)
# end of S3Handler class
