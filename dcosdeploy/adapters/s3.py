from urllib3 import PoolManager
from minio import Minio
from minio.error import NoSuchKey, NoSuchBucket
from ..base import APIRequestException


class S3FileAdapter:
    def __init__(self):
        self._servers = dict()

    def ping(self, server):
        try:
            client = self._init_client(server)
            client.bucket_exists("dcos-deploy-dummy")
            return True
        except:
            return False

    def files_equal(self, server, bucket, key, hash):
        """Returns true if the file in the bucket exists and has the same hash as the provided one"""
        client = self._init_client(server)
        try:
            stat = client.stat_object(bucket, key)
            return hash == self._hash_from_metadata(stat.metadata)
        except Exception:
            return None

    def upload_file(self, server, bucket, key, file_obj, file_size, hash):
        client = self._init_client(server)
        client.put_object(bucket, key, file_obj, file_size, metadata=dict(hash=hash, uploaded_by="dcos-deploy"))

    def get_file(self, server, bucket, key):
        client = self._init_client(server)
        response = client.get_object(bucket, key)
        if not response.readable():
            raise APIRequestException("Could not download file from S3", response)
        return response.read()
    
    def remove_file(self, server, bucket, key):
        client = self._init_client(server)
        client.remove_object(bucket, key)

    def does_file_exist(self, server, bucket, key):
        client = self._init_client(server)
        try:
            client.stat_object(bucket, key)
            return True
        except NoSuchKey:
            return False
        except NoSuchBucket:
            return False

    def does_bucket_exist(self, server, bucket):
        try:
            client = self._init_client(server)
            return client.bucket_exists(bucket)
        except Exception:
            return False

    def create_bucket(self, server, bucket):
        client = self._init_client(server)
        client.make_bucket(bucket)

    def set_bucket_policy(self, server, bucket, policy):
        client = self._init_client(server)
        client.set_bucket_policy(bucket, policy)

    def _hash_from_metadata(self, metadata):
        for key in metadata.keys():
            if key.lower() == "x-amz-meta-hash":
                return metadata[key]
        return ""

    def _init_client(self, server):
        server_id = server.id()
        if server_id not in self._servers:
            if not server.ssl_verify:
                pool = PoolManager(cert_reqs='CERT_NONE')
            else:
                pool = None
            self._servers[server_id] = Minio(server.endpoint, server.access_key, server.secret_key, secure=server.secure, http_client=pool)
        return self._servers[server_id]
