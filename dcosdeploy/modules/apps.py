import json
from dcosdeploy.adapters.marathon import MarathonAdapter
from dcosdeploy.util import compare_dicts, read_yaml


class MarathonApp(object):
    def __init__(self, name, app_id, app_definition):
        self.app_id = app_id
        self.app_definition = app_definition


def preprocess_config(base_name, base_config):
    if "_template" in base_config and "_vars" in base_config:
        marathon_filename = base_config["_template"]
        config = read_yaml(base_config["_vars"])
        defaults = config.get("defaults", dict())
        instances = config["instances"]
        for name, config in instances.items():
            only_restriction = None
            except_restriction = None
            if "only" in config:
                only_restriction = config["only"]
                del config["only"]
            if "except" in config:
                except_restriction = config["except"]
                del config["except"]
            extra_vars = config
            for key, value in defaults.items():
                if key not in extra_vars:
                    extra_vars[key] = value
            extra_vars["name"] = name
            instance_config = dict(marathon=marathon_filename, extra_vars=extra_vars, only=only_restriction)
            instance_config["except"] = except_restriction  # except not allowed as kwarg for dict()
            yield base_name+"-"+name, instance_config
    yield base_name, base_config


def parse_config(name, config, variables):
    path = config.get("path", None)
    app_definition_path = config.get("marathon")
    if not app_definition_path:
        raise Exception("Service %s has no marathon app definition" % name)
    extra_vars = config.get("extra_vars", dict())
    app_definition_path = variables.render(app_definition_path)
    with open(app_definition_path) as app_definition_file:
        app_definition = app_definition_file.read()
    app_definition = variables.render(app_definition, extra_vars)
    app_definition = json.loads(app_definition)
    if path:
        path = variables.render(path)
    else:
        path = app_definition["id"]
    return MarathonApp(name, path, app_definition)


class MarathonAppsManager(object):
    def __init__(self):
        self.api = MarathonAdapter()

    def deploy(self, config, dependencies_changed=False):
        print("\tStarting deployment...")
        changed = self.api.deploy_app(config.app_definition, True)
        if not changed and dependencies_changed:
            print("\tNo change in app config. Restarting app...")
            self.api.restart_app(config.app_id, True)
            print("\tRestart finished")
        else:
            print("\tFinished")
        return changed

    def dry_run(self, config, dependencies_changed=False, debug=False):
        app_state = self.api.get_app_state(config.app_id)
        if not app_state:
            print("Would create marathon app %s" % config.app_id)
            return True
        changed = not self.compare_app_definitions(app_state, config.app_definition, debug)
        if changed:
            print("Would possibly update marathon app %s" % config.app_id)
        elif dependencies_changed:
            print("Would restart marathon app %s" % config.app_id)
        return changed

    def compare_app_definitions(self, old_definition, new_definition, debug=False):
        for key in ["version", "lastTaskFailure", "tasks", "tasksHealthy", "tasksUnhealthy", "versionInfo", "deployments", "tasksRunning", "tasksStaged", "executor"]:
            if key in old_definition:
                del old_definition[key]
        return compare_dicts(old_definition, new_definition, print_differences=debug)


__config__ = MarathonApp
__manager__ = MarathonAppsManager
__config_name__ = "app"
