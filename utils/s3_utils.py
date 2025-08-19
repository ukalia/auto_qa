import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError
from auto_qa import settings
from utils.logger import Logger


logger = Logger(__name__).logger


class S3Client():
    def __init__(self):
        self.access_key_id = settings.AWS_ACCESS_KEY_ID
        self.secret_access_key = settings.AWS_SECRET_ACCESS_KEY
        self.bucket = settings.AWS_STORAGE_BUCKET_NAME
        self.endpoint = settings.AWS_S3_ENDPOINT_URL
        self.region = settings.AWS_S3_REGION_NAME
        self._client = None


    @property
    def client(self):
        if self._client is None:
            try:
                self._client = boto3.client(
                    's3',
                    aws_access_key_id=self.access_key_id,
                    aws_secret_access_key=self.secret_access_key,
                    endpoint_url=self.endpoint,
                    region_name=self.region,
                    config=Config(retries={'max_attempts':5, 'mode': 'standard'})
                )
                self._client.head_bucket(Bucket=self.bucket)
            except (ClientError, NoCredentialsError) as e:
                code = e.response.get('Error', {}).get('Code', '')
                if code in ('404', 'NoSuchBucket'):
                    logger.debug(f'Bucket {self.bucket} does not exist')
                else:
                    logger.error(f'Failed to initialize S3 client: {str(e)}')
                    raise
        return self._client

    @Logger.log_function_call(logger)
    @Logger.log_execution_time(logger)
    def get_object_metadata(self, object_key, include_etag=False):
        try:
            response = self.client.head_object(
                Bucket=self.bucket,
                Key=object_key
            )       
            result = {'status': True, 'last_modified': response['LastModified']}
            if include_etag:
                result['etag'] = response.get('ETag', '').strip('"')
            else:
                result['metadata'] = response.get('Metadata', {})
            logger.debug(f'Successfully fetched metadata for object {object_key} : {result}')

            return result
        except ClientError as e:
            code = e.response.get('Error', {}).get('Code', '')
            if code in ('404', 'NotFound', 'NoSuchKey'):
                logger.debug(f'Object not found {object_key}')
            else:
                logger.error(f'Error while fetching metadata for object {object_key}: {str(e)}')
            return {'status': False}

    @Logger.log_function_call(logger)
    @Logger.log_execution_time(logger)
    def upload_content_to_s3(self, content, object_key, content_type='text/plain', metadata=None):
        try:
            md = {'upload_source': 'auto_qa', 'content_encoding': 'utf-8'}
            if metadata:
                md.update(metadata)
            body = content

            if isinstance(content, str):
                body = content.encode('utf-8')
                
            if content_type in ('text/plain', 'application/json') and "charset=" not in content_type.lower():
                content_type = f'{content_type}; charset=utf-8'

            response = self.client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=body,
                ContentType=content_type,
                Metadata=md
            )
            etag = response.get('ETag', '').strip('"')
            logger.debug(f'Successfully uploaded object {object_key} to s3: {etag}')
            return {'status': True, 'etag': etag}
        except ClientError as e:
            logger.exception(f'Failed to upload object {object_key}: {str(e)}')
            return {'status': False}       

    @Logger.log_function_call(logger)
    @Logger.log_execution_time(logger)
    def download_content_from_s3(self, object_key, etag=None):
        try:
            params = {'Bucket': self.bucket, 'Key': object_key,}
            if etag:
                params['IfNoneMatch'] = f'"{etag}"'

            response = self.client.get_object(**params)
            content = response['Body'].read().decode('utf-8')
            logger.debug('Successfully downloaded data from s3')

            return {'status': True, 'content': content}
        except ClientError as e:
            code = e.response.get('Error', {}).get('Code', '')
            if code == '304':
                logger.debug(f'Etag unchanged')
                return {
                    'status': False,
                    'no_change_in_etag': True
                }
            if code in ('404', 'NotFound', 'NoSuchKey'):
                logger.debug(f'Object not found {object_key}')
                return {'status': False}
            logger.error(f'Failed to download content for object {object_key}: {str(e)}')
            return {'status': False}

    @Logger.log_function_call(logger)
    @Logger.log_execution_time(logger)
    def delete_object(self, object_key):
        try:
            self.client.delete_object(
                Bucket=self.bucket,
                Key=object_key
            )
            logger.info(f'Successfully deleted object {object_key}')
            return True
        except ClientError as e:
            logger.exception(f'Error while deleting object {object_key}: {str(e)}')
            return False

    @Logger.log_function_call(logger)
    @Logger.log_execution_time(logger)
    def object_exists(self, object_key):
        try:
            self.client.head_object(
                Bucket=self.bucket,
                Key=object_key
            )
            return True
        except ClientError as e:
            code = e.response.get('Error', {}).get('Code', '')
            if code in ('404', 'NotFound', 'NoSuchKey'):
                return False
            else:
                logger.exception(f'Error on checking object {object_key}: {str(e)}')
                return False

    @Logger.log_function_call(logger)
    @Logger.log_execution_time(logger)
    def create_bucket_if_not_exists(self):
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return True
        except ClientError as e:
            code = e.response.get('Error', {}).get('Code', '')
            if code in ('404', 'NoSuchBucket'):
                try:
                    self.client.create_bucket(Bucket=self.bucket, CreateBucketConfiguration={'LocationConstraint': self.region})
                    logger.info(f'Bucket created : {self.bucket}')
                    return True
                except ClientError as sub_e:
                    logger.exception(f'Failed to create bucket {self.bucket}: {str(sub_e)}')
            elif code == '403':
                logger.error(f'Access forbidden : {self.bucket}')
            else:
                logger.exception(f'Bucket access error: {e}')
            return False
