from minio import Minio
from minio.error import NoSuchKey


class S3FileAdapter(object):
    def __init__(self):
        pass

    def files_equal(self, server, bucket, key, hash):
        """Returns true if the file in the bucket exists and has the same hash as the provided one"""
        client = self._init_client(server)
        try:
            stat = client.stat_object(bucket, key)
            return hash == stat.metadata.get("x-amz-meta-hash", "")
        except NoSuchKey:
            return None

    def upload_file(self, server, bucket, key, file_obj, file_size, hash):
        client = self._init_client(server)
        client.put_object(bucket, key, file_obj, file_size, metadata=dict(hash=hash, uploaded_by="dcos-deploy"))

    def get_file(self, server, bucket, key):
        client = self._init_client(server)
        response = client.get_object(bucket, key)
        if not response.readable():
            raise Exception("Could not download file from S3")
        return response.read()


    def _init_client(self, server):
        return Minio(server.endpoint, server.access_key, server.secret_key, secure=True)
