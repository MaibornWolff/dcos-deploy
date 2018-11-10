import os
from dcosdeploy.adapters.s3 import S3FileAdapter
from dcosdeploy.base import ConfigurationException
from dcosdeploy.util import md5_hash, list_path_recursive


TMP_COMPRESS_NAME = "tmpcompressedfile"


class S3Server(object):
    def __init__(self, endpoint, access_key, secret_key):
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key


class S3File(object):
    def __init__(self, server, bucket, files, compress):
        self.server = server
        self.bucket = bucket
        self.files = files  # list of (s3_key, local_filename)
        self.compress = compress


def parse_config(name, config, config_helper):
    source = config.get("source")
    if not source:
        raise ConfigurationException("Field 'source' is required for s3file '%s'" % name)
    source = config_helper.render(source)
    destination = config.get("destination")
    if not destination:
        raise ConfigurationException("Field 'destination' is required for s3file '%s'" % name)
    server = config.get("server")
    if not server:
        raise ConfigurationException("Field 'server' is required for s3file '%s'" % name)
    bucket = destination.get("bucket")
    if not bucket:
        raise ConfigurationException("Field 'destination.bucket' is required for s3file '%s'" % name)
    bucket = config_helper.render(bucket)
    key = destination.get("key")
    if not key:
        raise ConfigurationException("Field 'destination.key' is required for s3file '%s'" % name)
    key = config_helper.render(key)

    endpoint = server.get("endpoint")
    if not endpoint:
        raise ConfigurationException("Field 'server.endpoint' is required for s3file '%s'" % name)
    endpoint = config_helper.render(endpoint)
    access_key = server.get("access_key")
    if not access_key:
        raise ConfigurationException("Field 'server.access_key' is required for s3file '%s'" % name)
    access_key = config_helper.render(access_key)
    secret_key = server.get("secret_key")
    if not secret_key:
        raise ConfigurationException("Field 'server.secret_key' is required for s3file '%s'" % name)
    secret_key = config_helper.render(secret_key)
    compress = config.get("compress")
    if compress:
        compress = config_helper.render(compress)
        if compress != "zip":
            raise ConfigurationException("Compression '%s' is not supported for s3file `%s`" % (compress, name))

    abspath = config_helper.abspath(source)
    if not os.path.exists(abspath):
        raise ConfigurationException("source '%s' does not exist in filesystem for s3file '%s'" % (source, name))
    basename = os.path.basename(source)
    if compress:
        if os.path.isdir(abspath):
            filelist = list()
            for filename in list_path_recursive(abspath):
                local_path = filename.replace(abspath, "").replace(os.path.sep, "/")
                if local_path[0] == "/":
                    local_path = local_path[1:]
                if basename:
                    local_path = os.path.join(basename, local_path)
                filelist.append((filename, local_path))
            files = [key, filelist]
        else:
            files = [key, [(abspath, os.path.basename(abspath))]]
    else:
        if os.path.isdir(abspath):
            files = list()
            for filename in list_path_recursive(abspath):
                local_path = filename.replace(abspath, "").replace(os.path.sep, "/")
                if local_path[0] == "/":
                    local_path = local_path[1:]
                if basename:
                    s3_key = key + "/" + basename + "/"
                else:
                    s3_key = key + "/"
                s3_key = s3_key + local_path
                files.append((s3_key, filename))
        else:
            files = [(key, abspath)]

    server = S3Server(endpoint, access_key, secret_key)
    return S3File(server, bucket, files, compress)


class S3FilesManager(object):
    def __init__(self):
        self.api = S3FileAdapter()

    def deploy(self, config, dependencies_changed=False, silent=False):
        if config.compress:
            try:
                self._compress_zip(config.files[1])
                hash = md5_hash(TMP_COMPRESS_NAME)
                if self.api.compare_file(config.server, config.bucket, config.files[0], hash):
                    print("\tNothing changed")
                    return False
                else:
                    print("\tUploading file to %s" % config.files[0])
                    with open(TMP_COMPRESS_NAME, "rb") as source_file:
                        file_stat = os.stat(TMP_COMPRESS_NAME)
                        self.api.upload_file(config.server, config.bucket, config.files[0], source_file, file_stat.st_size, hash)
                        print("\tUploaded file to %s" % config.files[0])
                    return True
            finally:
                os.remove(TMP_COMPRESS_NAME)
        else:
            changed = False
            for key, filename in config.files:
                hash = md5_hash(filename)
                if not self.api.compare_file(config.server, config.bucket, key, hash):
                    changed = True
                    print("\tUploading file to %s" % key)
                    with open(filename, "rb") as source_file:
                        file_stat = os.stat(filename)
                        self.api.upload_file(config.server, config.bucket, key, source_file, file_stat.st_size, hash)
                        print("\tUploaded file to %s" % key)
            if not changed:
                print("\tNothing changed")
            return changed

    def dry_run(self, config, dependencies_changed=False, print_changes=True, debug=False):
        if config.compress:
            try:
                self._compress_zip(config.files[1])
                return self._dry_run_single_file(config.server, config.bucket, config.files[0], TMP_COMPRESS_NAME)
            finally:
                os.remove(TMP_COMPRESS_NAME)
        for key, filename in config.files:
            changed = False
            if self._dry_run_single_file(config.server, config.bucket, key, filename):
                changed = True
        return changed

    def _dry_run_single_file(self, server, bucket, key, filename):
        hash = md5_hash(filename)
        if not self.api.compare_file(server, bucket, key, hash):
            print("Would upload file to %s" % key)
            return True
        return False

    def _compress_zip(self, files):
        from zipfile import ZipFile, ZIP_DEFLATED
        with ZipFile(TMP_COMPRESS_NAME, "w", compression=ZIP_DEFLATED) as zip_file:
            for local_path, arcname in files:
                zip_file.write(local_path, arcname)


__config__ = S3File
__manager__ = S3FilesManager
__config_name__ = "s3file"
