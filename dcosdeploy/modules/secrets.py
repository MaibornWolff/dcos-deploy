from dcosdeploy.adapters.secrets import SecretsAdapter
from dcosdeploy.base import ConfigurationException
from dcosdeploy.util import print_if


class Secret(object):
    def __init__(self, name, path, value, file_content):
        self.name = name
        self.path = path
        self.value = value
        self.file_content = file_content
        self.dependencies = list()


def parse_config(name, config, config_helper):
    path = config.get("path")
    if not path:
        raise ConfigurationException("Path is required for secret '%s'" % name)
    value = config.get("value")
    file_path = config.get("file")
    render = config.get("render", False)
    path = config_helper.render(path)
    if value:
        value = config_helper.render(value)
        file_content = None
    elif file_path:
        file_path = config_helper.render(file_path)
        file_content = config_helper.read_file(file_path, render_variables=render, as_binary=not render)
    else:
        raise ConfigurationException("Either value or file are required for secret '%s'" % name)
    return Secret(name, path, value, file_content)


class SecretsManager(object):
    def __init__(self):
        self.api = SecretsAdapter()

    def deploy(self, config, dependencies_changed=False, silent=False):
        exists = config.path in self.api.list_secrets()
        if exists:
            content = self.api.get_secret(config.path)
            if config.value:
                changed = content != config.value
            elif config.file_content:
                if isinstance(config.file_content, str):
                    content = content.decode("utf-8")
                changed = content != config.file_content
            else:
                raise Exception("Specified neither value nor file_content for secret")
            if not changed:
                print_if(not silent, "\tSecret already exists. No update needed.")
                return False
            print_if(not silent, "\tUpdating secret")
            self.api.write_secret(config.path, config.value, config.file_content, update=exists)
            print_if(not silent, "\tSecret updated.")
            return True
        else:
            print_if(not silent, "\tCreating secret")
            self.api.write_secret(config.path, config.value, config.file_content, update=exists)
            print_if(not silent, "\tSecret created.")
            return True

    def dry_run(self, config, dependencies_changed=False, print_changes=True, debug=False):
        exists = config.path in self.api.list_secrets()
        if not exists:
            print("Would create secret %s" % config.path)
            return True
        content = self.api.get_secret(config.path)
        if config.value:
            changed = content != config.value
        elif config.file_content:
            if isinstance(config.file_content, str):
                content = content.decode("utf-8")
            changed = content != config.file_content
        else:
            raise Exception("Specified neither value nor file_content for secret")
        if changed:
            if debug:
                print("Would update secret %s from %s to %s" % (config.path, content, config.file_content))
            else:
                print("Would update secret %s" % config.path)
        return changed


__config__ = Secret
__manager__ = SecretsManager
__config_name__ = "secret"
