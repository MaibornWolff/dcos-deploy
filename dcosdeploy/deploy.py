from .config import read_config


class DeploymentRunner(object):
    def __init__(self, config_filename, provided_variables, debug_mode):
        self.already_deployed = dict()
        self.dry_deployed = dict()
        self.debug_mode = debug_mode
        self.config, self.dependencies, self.managers = read_config(config_filename, provided_variables)

    def run_deployment(self):
        for name, deployment_object in self.config.items():
            self.deploy(name, deployment_object)

    def run_partial_deployment(self, only):
        deployment_object = self.config.get(only)
        if not deployment_object:
            raise Exception("Could not find %s" % only)
        self.deploy(only, deployment_object)

    def deploy(self, name, config):
        if name in self.already_deployed:
            return self.already_deployed[name]
        dependency_changed = False
        for dependency_name, dependency, dependency_type in self.dependencies.get(name, list()):
            if self.deploy(dependency_name, dependency) and dependency_type == "update":
                dependency_changed = True
        changed = False
        found = False
        for config_type, manager in self.managers.items():
            if isinstance(config, config_type):
                print("Deploying %s:" % name)
                changed = manager.deploy(config, dependencies_changed=dependency_changed)
                found = True
                break
        if not found:
            print("Not yet implemented: %s" % config)
        self.already_deployed[name] = changed
        return changed

    def dry_run(self):
        changed = False
        for name, deployment_object in self.config.items():
            if self.dry_deploy(name, deployment_object):
                changed = True
        return changed

    def partial_dry_run(self, only):
        deployment_object = self.config.get(only)
        if not deployment_object:
            raise Exception("Could not find %s" % only)
        return self.dry_deploy(only, deployment_object)

    def dry_deploy(self, name, config):
        if name in self.dry_deployed:
            return self.dry_deployed[name]
        dependency_changed = False
        for dependency_name, dependency, dependency_type in self.dependencies.get(name, list()):
            if self.dry_deploy(dependency_name, dependency) and dependency_type == "update":
                dependency_changed = True
        changed = False
        found = False
        for config_type, manager in self.managers.items():
            if isinstance(config, config_type):
                changed = manager.dry_run(config, dependencies_changed=dependency_changed)
                found = True
                break
        if not found:
            print("Not yet implemented: %s" % config)
        self.dry_deployed[name] = changed
        return changed
