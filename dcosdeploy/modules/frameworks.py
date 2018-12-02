from dcosdeploy.adapters.cosmos import CosmosAdapter
from dcosdeploy.util import compare_dicts, print_if
from dcosdeploy.base import ConfigurationException


class Framework(object):
    def __init__(self, name, path, package_name, package_version, options):
        self.service_name = path
        self.package_name = package_name
        self.package_version = package_version
        self.options = options


def parse_config(name, config, config_helper):
    path = config.get("path", None)
    package = config.get("package")
    options_path = package.get("options")
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
    package_name = config_helper.render(package_name)
    package_version = config_helper.render(package_version)
    return Framework(name, path, package_name, package_version, options)


class FrameworksManager(object):
    def __init__(self):
        self.api = CosmosAdapter()

    def deploy(self, config, dependencies_changed=False, silent=False):
        changed = self.dry_run(config, dependencies_changed=False, print_changes=False)
        if not changed:
            print_if(not silent, "\tConfig unchanged.")
            return
        old_description = self.api.describe_service(config.service_name)
        package_version = config.package_version
        if not old_description:
            print_if(not silent, "\tInstalling framework")
            self.api.install_package(config.service_name, config.package_name, config.package_version, config.options)
            if config.package_name == "edgelb":
                print_if(not silent, "\tPackage is Edge-LB. Waiting is disabled.")
            else:
                print_if(not silent, "\tWaiting for deployment to finish")
                self.api.wait_for_plan_complete(config.service_name, "deploy")
        else:
            if old_description["package"]["version"] == config.package_version:
                package_version = None
            print_if(not silent, "\tUpdating framework")
            self.api.update_service(config.service_name, package_version, config.options)
            # Do not wait for completion after update, assume update is done in rolling fashion
        print_if(not silent, "\tFinished")
        return changed

    def dry_run(self, config, dependencies_changed=False, print_changes=True, debug=False):
        description = self.api.describe_service(config.service_name)
        if not description:
            if print_changes:
                print("Would install %s" % config.service_name)
            return True
        old_options = description["userProvidedOptions"]
        options_equal = compare_dicts(config.options, old_options, print_differences=debug)
        version_equal = description["package"]["version"] == config.package_version
        if not version_equal:
            if print_changes:
                print("Would update %s from %s to %s" % (config.service_name, description["package"]["version"], config.package_version))
        elif not options_equal:
            if print_changes:
                print("Would change config of %s" % config.service_name)
        return not options_equal or not version_equal


__config__ = Framework
__manager__ = FrameworksManager
__config_name__ = "framework"
