import time
from ..adapters.cosmos import CosmosAdapter
from ..adapters.marathon import MarathonAdapter
from ..util import compare_dicts
from ..util.output import echo, echo_diff
from ..base import ConfigurationException


class Framework(object):
    def __init__(self, name, service_name, app_id, package_name, package_version, options):
        self.service_name = service_name
        self.app_id = app_id
        self.package_name = package_name
        self.package_version = package_version
        self.options = options


def parse_config(name, config, config_helper):
    path = config.get("path", None)
    package = config.get("package")
    options_path = package.get("options")
    app_id = config.get("appid")
    if not options_path:
        raise Exception("Service %s has no options file" % name)
    options_path = config_helper.render(options_path)
    options = config_helper.read_json(options_path, render_variables=True)
    if path:
        path = config_helper.render(path)
    else:
        path = options["service"]["name"]
    package_name = package.get("name")
    if not package_name:
        raise ConfigurationException("package.name is required")
    package_version = package.get("version")
    if not package_version:
        raise ConfigurationException("package.version is required")
    if not app_id:
        # special case because edgelb installs scheduler as <path>/api
        if package_name == "edgelb":
            app_id = path + "/api"
        else:
            app_id = path
    package_name = config_helper.render(package_name)
    package_version = config_helper.render(package_version)
    return Framework(name, path, app_id, package_name, package_version, options)


class FrameworksManager(object):
    def __init__(self):
        self.api = CosmosAdapter()
        self.marathon = MarathonAdapter()

    def deploy(self, config, dependencies_changed=False, force=False):
        old_description = self.api.describe_service(config.app_id)
        package_version = config.package_version
        if not old_description:
            echo("\tInstalling framework")
            self.api.install_package(config.service_name, config.package_name, config.package_version, config.options)
            echo("\tWaiting for framework to start")
            self.marathon.wait_for_deployment(config.app_id)
            time.sleep(5)  # Wait a few seconds for admin-lb to catch up
            if self.api.has_plans_api(config.app_id):
                echo("\tWaiting for deployment plan to finish")
                self.api.wait_for_plan_complete(config.app_id, "deploy")
        else:
            old_options = old_description["userProvidedOptions"]
            options_diff = compare_dicts(old_options, config.options)
            version_equal = old_description["package"]["version"] == config.package_version
            if version_equal and not options_diff and dependencies_changed:
                echo("\tNo change in config. Restarting framework")
                self.marathon.restart_app(config.app_id)
            else:
                if version_equal:
                    package_version = None
                echo("\tUpdating framework")
                self.api.update_service(config.app_id, package_version, config.options)
                # Do not wait for completion after update, assume update is done in rolling fashion
        echo("\tFinished")
        return True

    def dry_run(self, config, dependencies_changed=False):
        description = self.api.describe_service(config.app_id)
        if not description:
            echo("Would install %s" % config.service_name)
            return True
        old_options = description["userProvidedOptions"]
        options_diff = compare_dicts(old_options, config.options)
        version_equal = description["package"]["version"] == config.package_version
        if not version_equal:
            echo("Would update %s from %s to %s" % (config.service_name, description["package"]["version"], config.package_version))
        if options_diff:
            echo_diff("Would change config of %s" % config.service_name, options_diff)
        if dependencies_changed and version_equal and not options_diff and not self.api.has_plans_api(config.service_name):
            echo("Would restart framework %s" % config.service_name)
            return True
        return options_diff or not version_equal

    def delete(self, config, force=False):
        echo("\tDeleting framework")
        self.api.uninstall_package(config.app_id, config.package_name)
        echo("\tDeleted framework. Waiting for uninstall to complete")
        self.marathon.wait_for_deletion(config.app_id)
        echo("\tUninstall complete.")
        return True

    def dry_delete(self, config):
        if self.api.describe_service(config.app_id):
            echo("Would delete framework %s" % config.service_name)
            return True
        else:
            return False


__config__ = Framework
__manager__ = FrameworksManager
__config_name__ = "framework"
