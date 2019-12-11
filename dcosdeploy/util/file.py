import os
import oyaml as yaml
from ..base import ConfigurationException


def detect_yml_file(base):
    for choice in [".yml", ".yaml"]:
        if os.path.exists(base+choice):
            return base+choice
    raise ConfigurationException("Could not find yaml file %s.yml" % base)


def read_yaml(filename):
    with open(filename) as yaml_file:
        data = yaml_file.read()
    return yaml.safe_load(data)


def list_path_recursive(path):
    for dirpath, subdirs, filenames in os.walk(path):
        for filename in filenames:
            yield os.path.join(dirpath, filename)
