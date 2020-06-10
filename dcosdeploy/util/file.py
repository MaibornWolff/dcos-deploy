import os
import oyaml as yaml
from ..base import ConfigurationException
from .output import echo_error


def detect_yml_file(base):
    for choice in [".yml", ".yaml"]:
        if os.path.exists(base+choice):
            return [base+choice]
    raise ConfigurationException("Could not find yaml file %s.yml" % base)


def read_yaml(filename):
    with open(filename) as yaml_file:
        data = yaml_file.read()
    return yaml.safe_load(data)


def check_if_encrypted_is_older(path):
    base_path = path
    if base_path.endswith(".encrypted") or base_path.endswith(".enc"):
        base_path = base_path.rsplit(".", 1)[0]
    for suffix in ["", ".clear", ".decrypted"]:
        if os.path.exists(base_path + suffix):
            decrypted_path = base_path + suffix
            mtime_encrypted_file = os.path.getmtime(path)
            mtime_decrypted_file = os.path.getmtime(decrypted_path)
            if mtime_decrypted_file > mtime_encrypted_file:
                echo_error("WARNING: %s is newer than %s. Did you forget to reencrypt it?" % (decrypted_path, path))
            return


def list_path_recursive(path):
    for dirpath, subdirs, filenames in os.walk(path):
        for filename in filenames:
            yield os.path.join(dirpath, filename)
