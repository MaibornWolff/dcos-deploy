from .config import read_config
from .adapters.dcos import fail_on_missing_connectivity
from .util.output import echo


class DeletionRunner:
    def __init__(self, config_filename, provided_variables):
        fail_on_missing_connectivity()
        self._already_deleted = dict()  # entitiy-name -> newly deleted
        self._dry_deleted = dict()  # entity-name -> newly deleted
        self._config, self._managers = read_config(config_filename, provided_variables)
        self._calculate_reserve_dependencies()

    def run_deletion(self):
        for name, deployment_object in self._config.items():
            self._delete(name, deployment_object)

    def run_partial_deletion(self, only):
        deployment_object = self._config.get(only)
        if not deployment_object:
            raise Exception("Could not find %s" % only)
        self._delete(only, deployment_object)

    def dry_run(self):
        to_delete = False
        for name, deployment_object in self._config.items():
            if self._dry_delete(name, deployment_object):
                to_delete = True
        return to_delete

    def partial_dry_run(self, only, force=False):
        deployment_object = self._config.get(only)
        if not deployment_object:
            raise Exception("Could not find %s" % only)
        return self._dry_delete(only, deployment_object)

    def _delete(self, name, config):
        if name in self._already_deleted:
            return self._already_deleted[name]
        for dependency_name in config.reverse_dependencies:
            dependency = self._config[dependency_name]
            self._delete(dependency_name, dependency)
        manager = self._managers[config.entity_type]
        if not manager:
            raise Exception("Could not find manager for '%s'" % config.entity_type)
        if not hasattr(manager, "delete"):
            echo("Module %s does not yet support deletion. Not deleting entity '%s'" % (config.entity_type, name))
            return False
        echo("Deleting %s:" % name)
        deleted = manager.delete(config.entity)
        self._already_deleted[name] = deleted
        return deleted

    def _dry_delete(self, name, config):
        if name in self._dry_deleted:
            return self._dry_deleted[name]
        to_delete = False
        for dependency_name in config.reverse_dependencies:
            dependency = self._config[dependency_name]
            if self._dry_delete(dependency_name, dependency):
                to_delete = True
        manager = self._managers[config.entity_type]
        if not manager:
            raise Exception("Could not find manager for '%s'" % config.entity_type)
        if not hasattr(manager, "dry_delete"):
            echo("Module %s does not yet support deletion. Not deleting entity '%s'" % (config.entity_type, name))
            return to_delete
        deleted = manager.dry_delete(config.entity)
        if not deleted:
            self._already_deleted[name] = False
        self._dry_deleted[name] = deleted
        return deleted or to_delete

    def _calculate_reserve_dependencies(self):
        for name, deployment_object in self._config.items():
            for dependency_name, _ in deployment_object.dependencies:
                dependency = self._config[dependency_name]
                dependency.reverse_dependencies.append(name)