from dcosdeploy.adapters.secrets import SecretsAdapter
from dcosdeploy.base import ConfigurationException


class Secret(object):
    def __init__(self, name, path, value, file_content):
        self.name = name
        self.path = path
        self.value = value
        self.file_content = file_content
        self.dependencies = list()

    def full_path(self):
        return "secret:"+self.name


def parse_config(name, config, variables):
    path = config.get("path")
    if not path:
        raise ConfigurationException("Path is required for secret '%s'" % name)
    value = config.get("value")
    file_path = config.get("file")
    path = variables.render(path)
    if value:
        value = variables.render(value)
        file_content = None
    elif file_path:
        file_path = variables.render(file_path)
        with open(file_path) as secret_file:
            file_content = secret_file.read()
    else:
        raise ConfigurationException("Either value or file are required for secret '%s'" % name)
    return Secret(name, path, value, file_content)


class SecretsManager(object):
    def __init__(self):
        self.api = SecretsAdapter()

    def deploy(self, config, dependencies_changed=False):
        exists = config.path in self.api.list_secrets()
        if exists:
            content = self.api.get_secret(config.path)
            if config.value:
                changed = content != config.value
            elif config.file_content:
                changed = content != config.file_content
            else:
                raise Exception("Specified neither value nor file_content for secret")
            if not changed:
                print("\tSecret already exists. No update needed.")
                return False
            print("\tUpdating secret")
            self.api.write_secret(config.path, config.value, config.file_content, update=exists)
            print("\tSecret updated.")
            return True
        else:
            print("\tCreating secret")
            self.api.write_secret(config.path, config.value, config.file_content, update=exists)
            print("\tSecret created.")
            return True

    def dry_run(self, config, dependencies_changed=False, debug=False):
        exists = config.path in self.api.list_secrets()
        if not exists:
            print("Would create secret %s" % config.path)
            return True
        content = self.api.get_secret(config.path)
        if config.value:
            changed = content != config.value
        elif config.file_content:
            changed = content != config.file_content
        else:
            raise Exception("Specified neither value nor file_content for secret")
        if changed:
            print("Would update secret %s" % config.path)


__config__ = Secret
__manager__ = SecretsManager
__config_name__ = "secret"
