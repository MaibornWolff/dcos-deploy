from ..adapters.secrets import SecretsAdapter
from ..base import ConfigurationException
from ..util import compare_text
from ..util.output import echo, echo_diff


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
    if path[0] == '/':
        path = path[1:]
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

    def deploy(self, config, dependencies_changed=False, force=False):
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
            if not changed and not force:
                echo("\tSecret already exists. No update needed.")
                return False
            echo("\tUpdating secret")
            self.api.write_secret(config.path, config.value, config.file_content, update=exists)
            echo("\tSecret updated.")
            return True
        else:
            echo("\tCreating secret")
            self.api.write_secret(config.path, config.value, config.file_content, update=exists)
            echo("\tSecret created.")
            return True

    def dry_run(self, config, dependencies_changed=False):
        exists = config.path in self.api.list_secrets()
        if not exists:
            echo("Would create secret %s" % config.path)
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
            new_content = config.file_content if config.file_content else config.value
            echo_diff("Would update secret %s" % config.path, compare_text(content, new_content))
        return changed

    def delete(self, config, force=False):
        echo("\tDeleting secret")
        deleted = self.api.delete_secret(config.path)
        echo("\tDeleted secret.")
        return deleted

    def dry_delete(self, config):
        if self.api.get_secret(config.path):
            echo("Would delete secret %s" % config.path)
            return True
        else:
            return False


__config__ = Secret
__manager__ = SecretsManager
__config_name__ = "secret"
