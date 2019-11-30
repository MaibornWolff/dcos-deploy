from .config import read_config, StateEnum
from .adapters.dcos import fail_on_missing_connectivity


class DeploymentRunner(object):
    def __init__(self, config_filename, provided_variables, debug_mode):
        fail_on_missing_connectivity()
        self.already_deployed = dict()  # entitiy-name -> changed
        self.dry_deployed = dict()  # entity-name -> changed
        self.debug_mode = debug_mode
        self.config, self.managers = read_config(config_filename, provided_variables)

    def run_deployment(self, force=False):
        for name, deployment_object in self.config.items():
            self.deploy(name, deployment_object, force=force)

    def run_partial_deployment(self, only, force=False):
        deployment_object = self.config.get(only)
        if not deployment_object:
            raise Exception("Could not find %s" % only)
        self.deploy(only, deployment_object, force=force)

    def deploy(self, name, config, force=False):
        if name in self.already_deployed:
            return self.already_deployed[name]
        dependency_changed = False
        for dependency_name, dependency_type in config.dependencies:
            dependency = self.config[dependency_name]
            if self.deploy(dependency_name, dependency) and dependency_type == "update":
                dependency_changed = True
        manager = self.managers[config.entity_type]
        if not manager:
            raise Exception("Could not find manager for '%s'" % config.entity_type)
        if config.when_condition == "dependencies-changed" and not dependency_changed and not force:
            changed = False
        else:
            print("Deploying %s:" % name)
            if config.state == StateEnum.REMOVED:
                changed = manager.delete(config.entity, force=force)
            else:
                changed = manager.deploy(config.entity, dependencies_changed=dependency_changed, force=force)
        self.already_deployed[name] = changed
        return changed

    def dry_run(self):
        changed = False
        for name, deployment_object in self.config.items():
            if self.dry_deploy(name, deployment_object):
                changed = True
        return changed

    def partial_dry_run(self, only, force=False):
        deployment_object = self.config.get(only)
        if not deployment_object:
            raise Exception("Could not find %s" % only)
        return self.dry_deploy(only, deployment_object, force=force)

    def dry_deploy(self, name, config, force=False):
        if name in self.dry_deployed:
            return self.dry_deployed[name]
        dependency_changed = False
        for dependency_name, dependency_type in config.dependencies:
            dependency = self.config[dependency_name]
            if self.dry_deploy(dependency_name, dependency) and dependency_type == "update":
                dependency_changed = True
        if force:
            dependency_changed = True
        manager = self.managers[config.entity_type]
        if not manager:
            raise Exception("Could not find manager for '%s'" % config.entity_type)
        if config.when_condition == "dependencies-changed" and not dependency_changed:
            changed = False
        else:
            if config.state == StateEnum.REMOVED:
                changed = manager.dry_delete(config.entity)
            else:
                changed = manager.dry_run(config.entity, dependencies_changed=dependency_changed, debug=self.debug_mode)
        if not changed and not force:
            self.already_deployed[name] = False
        self.dry_deployed[name] = changed
        if force:
            changed = True
        return changed
