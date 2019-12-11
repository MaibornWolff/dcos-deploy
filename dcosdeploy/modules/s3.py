import os
from io import BytesIO
from ..adapters.s3 import S3FileAdapter
from ..base import ConfigurationException
from ..util import md5_hash, md5_hash_bytes, md5_hash_str, list_path_recursive, compare_text
from ..util.output import echo, echo_diff
from ..util import global_config


class S3Server(object):
    def __init__(self, endpoint, access_key, secret_key, ssl_verify, secure):
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.ssl_verify = ssl_verify
        self.secure = secure


class S3File(object):
    def __init__(self, server, bucket, files, compress, create_bucket, bucket_policy):
        self.server = server
        self.bucket = bucket
        self.files = files  # list of (s3_key, local_filename) or (key, list of (filename, path in zip))
        self.compress = compress
        self.create_bucket = create_bucket
        self.bucket_policy = bucket_policy


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
    create_bucket = destination.get("create_bucket", False)
    bucket_policy = destination.get("bucket_policy")
    if bucket_policy:
        bucket_policy = config_helper.render(bucket_policy)

    compress = config.get("compress")
    if compress:
        compress = config_helper.render(compress)
        if compress != "zip":
            raise ConfigurationException("Compression '%s' is not supported for s3file `%s`" % (compress, name))

    files = _collect_files(name, source, key, compress, config_helper)
    server = _parse_server_config(name, server, config_helper)
    return S3File(server, bucket, files, compress, create_bucket, bucket_policy)


def _parse_server_config(name, server, config_helper):
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
    ssl_verify = server.get("ssl_verify", True)
    secure = server.get("secure", True)
    return S3Server(endpoint, access_key, secret_key, ssl_verify, secure)


def _collect_files(name, source, key, compress, config_helper):
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
    return files


class S3FilesManager(object):
    def __init__(self):
        self.api = S3FileAdapter()

    def deploy(self, config, dependencies_changed=False, force=False):
        if config.create_bucket and not self.api.does_bucket_exist(config.server, config.bucket):
            echo("\tCreating bucket %s" % config.bucket)
            self.api.create_bucket(config.server, config.bucket)
            echo("\tCreated bucket %s" % config.bucket)
            if config.bucket_policy:
                self.api.set_bucket_policy(config.server, config.bucket, config.bucket_policy)
                echo("\tSet policy for bucket %s" % config.bucket)
        if config.compress:
            zip_obj = self._compress_zip(config.files[1])
            size = zip_obj.tell()
            zip_obj.seek(0)
            hash = self._hash_for_file_list(config.files[1])
            echo("\tUploading file to %s" % config.files[0])
            self.api.upload_file(config.server, config.bucket, config.files[0], zip_obj, size, hash)
            echo("\tUploaded file to %s" % config.files[0])
            return True
        else:
            changed = False
            for key, filename in config.files:
                with open(filename, "rb") as source_file:
                    hash = md5_hash_bytes(source_file)
                    source_file.seek(0)
                    if force or not self.api.files_equal(config.server, config.bucket, key, hash):
                        changed = True
                        echo("\tUploading file to %s" % key)
                        file_stat = os.stat(filename)
                        self.api.upload_file(config.server, config.bucket, key, source_file, file_stat.st_size, hash)
                        echo("\tUploaded file to %s" % key)
            if not changed:
                echo("\tNothing changed")
            return changed

    def dry_run(self, config, dependencies_changed=False):
        if config.create_bucket and not self.api.does_bucket_exist(config.server, config.bucket):
            echo("Would create bucket %s" % config.bucket)
        if config.compress:
            hash = self._hash_for_file_list(config.files[1])
            files_equal = self.api.files_equal(config.server, config.bucket, config.files[0], hash)
            if files_equal is None:
                echo("Would upload file to %s" % config.files[0])
                return True
            elif not files_equal:
                if global_config.debug:
                    echo("Would upload file to %s. Changes:" % config.files[0])
                    self._print_diffs_for_zip(self.api.get_file(config.server, config.bucket, config.files[0]), config.files[1])
                else:
                    echo("Would upload file to %s due to changes" % config.files[0])
                return True
            else:
                return False
        else:
            changed = False
            for key, filename in config.files:
                if self._dry_run_single_file(config.server, config.bucket, key, filename, global_config.debug):
                    changed = True
            return changed

    def delete(self, config, force=False):
        if config.compress:
            echo("\tRemoving file %s" % config.files[0])
            self.api.remove_file(config.server, config.bucket, config.files[0])
            echo("\tRemoved file.")
            return True
        else:
            for key, _ in config.files:
                echo("\tRemoving %s" % key)
                self.api.remove_file(config.server, config.bucket, key)
            echo("\tRemoved all files.")
            return True

    def dry_delete(self, config):
        if config.compress:
            if self.api.does_file_exist(config.server, config.bucket, config.files[0]):
                echo("Would remove file %s" % config.files[0])
                return True
            else:
                return False
        else:
            something_gets_removed = False
            for key, _ in config.files:
                if self.api.does_file_exist(config.server, config.bucket, key):
                    echo("Would remove file %s" % key)
                    something_gets_removed = True
            return something_gets_removed

    def _dry_run_single_file(self, server, bucket, key, filename, debug):
        hash = md5_hash(filename)
        files_equal = self.api.files_equal(server, bucket, key, hash)
        if files_equal is None:
            echo("Would upload file to %s" % key)
            return True
        elif not files_equal:
            if global_config.debug:
                echo("Would upload file to %s. Changes:" % key)
                server_file_content = self.api.get_file(server, bucket, key)
                with open(filename, "r") as local_file:
                    local_file_content = local_file.read()
                echo(compare_text(server_file_content, local_file_content))
            else:
                echo("Would upload file to %s due to changes" % key)
            return True
        return False

    def _print_diffs_for_zip(self, remote_file, files):
        from zipfile import ZipFile
        with ZipFile(BytesIO(remote_file), "r") as zip_file:
            local_files = dict(map(lambda tup: (tup[1], tup[0]), files))
            for name in zip_file.namelist():
                if name not in local_files:
                    echo("  %s will be deleted" % name)
                else:
                    with zip_file.open(name, "r") as remote_file:
                        remote_file_content = remote_file.read()
                    with open(local_files[name], "r") as local_file:
                        local_file_content = local_file.read()
                    diff = compare_text(remote_file_content, local_file_content)
                    if diff:
                        echo("  %s changed:" % name)
                        echo(diff)
            for name in local_files.keys():
                if name not in zip_file.namelist():
                    echo("  %s will be added" % name)

    def _hash_for_file_list(self, files):
        hash_list = list()
        for local_path, arcname in sorted(files, key=lambda i: i[1]):
            hash_list.append("%s %s" % (arcname, md5_hash(local_path)))
        hash_str = ','.join(hash_list)
        return md5_hash_str(hash_str.encode("utf-8"))

    def _compress_zip(self, files):
        from zipfile import ZipFile, ZIP_DEFLATED
        zip_object = BytesIO()
        with ZipFile(zip_object, "w", compression=ZIP_DEFLATED) as zip_file:
            for local_path, arcname in sorted(files, key=lambda i: i[1]):
                zip_file.write(local_path, arcname)
        return zip_object


__config__ = S3File
__manager__ = S3FilesManager
__config_name__ = "s3file"
