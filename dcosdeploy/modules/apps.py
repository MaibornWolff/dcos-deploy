import json
from copy import deepcopy
from dcosdeploy.base import ConfigurationException
from dcosdeploy.adapters.marathon import MarathonAdapter
from dcosdeploy.util import compare_dicts, print_if, update_dict_with_defaults


class MarathonApp(object):
    def __init__(self, name, app_id, app_definition):
        self.app_id = app_id
        self.app_definition = app_definition


def preprocess_config(base_name, base_config, config_helper):
    if "_template" in base_config and "_vars" in base_config:
        marathon_filename = base_config["_template"]
        config = config_helper.read_yaml(base_config["_vars"])
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


def parse_config(name, config, config_helper):
    path = config.get("path", None)
    app_definition_path = config.get("marathon")
    if not app_definition_path:
        raise ConfigurationException("Service %s has no marathon app definition" % name)
    extra_vars = config.get("extra_vars", dict())
    app_definition_path = config_helper.render(app_definition_path)
    app_definition = config_helper.read_file(app_definition_path)
    app_definition = config_helper.render(app_definition, extra_vars)
    app_definition = json.loads(app_definition)
    if path:
        path = config_helper.render(path)
    else:
        path = app_definition["id"]
    return MarathonApp(name, path, app_definition)


class MarathonAppsManager(object):
    def __init__(self):
        self.api = MarathonAdapter()

    def deploy(self, config, dependencies_changed=False, silent=False):
        print_if(not silent, "\tStarting deployment...")
        changed = self.api.deploy_app(config.app_definition, True)
        if not changed and dependencies_changed:
            print_if(not silent, "\tNo change in app config. Restarting app...")
            self.api.restart_app(config.app_id, True)
            print_if(not silent, "\tRestart finished")
        else:
            print_if(not silent, "\tFinished")
        return changed

    def dry_run(self, config, dependencies_changed=False, print_changes=True, debug=False):
        app_state = self.api.get_app_state(config.app_id)
        if not app_state:
            print("Would create marathon app %s" % config.app_id)
            return True
        changed = not self.compare_app_definitions(config.app_definition, app_state, debug)
        if changed:
            print("Would update marathon app %s" % config.app_id)
        elif dependencies_changed:
            print("Would restart marathon app %s" % config.app_id)
        return changed or dependencies_changed

    def compare_app_definitions(self, local_definition, remote_definition, debug=False):
        local_definition = deepcopy(local_definition)
        for key in ["version", "lastTaskFailure", "tasks", "tasksHealthy", "tasksUnhealthy", "versionInfo", "deployments", "tasksRunning", "tasksStaged"]:
            if key in remote_definition:
                del remote_definition[key]
        local_definition, remote_definition = _normalize_app_definition(local_definition, remote_definition)
        return compare_dicts(local_definition, remote_definition, print_differences=debug)


_app_defaults = dict(
    backoffFactor=1.15,
    backoffSeconds=1,
    cmd="",
    constraints=[],
    env={},
    executor="",
    fetch=[],
    healthChecks=[],
    disk=0,
    gpus=0,
    killSelection="YOUNGEST_FIRST",
    labels={},
    maxLaunchDelaySeconds=3600,
    requirePorts=False,
    unreachableStrategy={
        "expungeAfterSeconds": 0,
        "inactiveAfterSeconds": 0
    },
    upgradeStrategy={
        "maximumOverCapacity": 1,
        "minimumHealthCapacity": 1
    },
    networks=[
        {"mode": "host"}
    ],
    container={
        "type": "MESOS",
        "volumes": []
    },
)

_docker_defaults = dict(
    parameters=[],
    privileged=False,
    forcePullImage=False,
)

_health_check_defaults = dict(
    delaySeconds=15,
    gracePeriodSeconds=300,
    intervalSeconds=60,
    ipProtocol="IPv4",
    maxConsecutiveFailures=3,
    protocol="HTTP",
    timeoutSeconds=20,
)


def _normalize_app_definition(local_definition, remote_definition):
    update_dict_with_defaults(local_definition, _app_defaults)
    update_dict_with_defaults(remote_definition, _app_defaults)
    if local_definition["id"][0] != "/":
        local_definition["id"] = "/" + local_definition["id"]
    if "docker" in local_definition["container"]:
        update_dict_with_defaults(local_definition["container"]["docker"], _docker_defaults)

    if "portDefinitions" in remote_definition and "portDefinitions" not in local_definition:
        if len(remote_definition["portDefinitions"]) > 0:
            local_definition["portDefinitions"] = [{'protocol': 'tcp', 'port': 0, 'name': 'default'}]
        else:
            local_definition["portDefinitions"] = []
    local_container = local_definition["container"]
    remote_container = remote_definition["container"]
    if "portMappings" in remote_container and "portMappings" not in local_container:
        local_container["portMappings"] = [{
            "containerPort": 0,
            "labels": {},
            "name": "default",
            "protocol": "tcp",
            "servicePort": 0
        }]

    for local_mapping, remote_mapping in zip(local_definition["container"].get("portMappings", list()),
                                             remote_definition["container"].get("portMappings", list())):
        if local_mapping.get("servicePort", 0) == 0:
            if "servicePort" in local_mapping:
                del local_mapping["servicePort"]
            del remote_mapping["servicePort"]
        local_mapping.setdefault("protocol", "tcp")
        if "hostPort" in remote_mapping and "hostPort" not in local_mapping:
            local_mapping["hostPort"] = 0
    for local_def, remote_def in zip(local_definition.get("portDefinitions", list()), remote_definition.get("portDefinitions", list())):
        if local_def.get("port", 0) == 0:
            if "port" in local_def:
                del local_def["port"]
            del remote_def["port"]
        local_def.setdefault("protocol", "tcp")
        if "hostPort" in remote_def and "hostPort" not in local_def:
            local_def["hostPort"] = 0
    for health_check in local_definition["healthChecks"]:
        update_dict_with_defaults(health_check, _health_check_defaults)

    has_local_persistent_volume = False
    for volume in local_container["volumes"]:
        if "persistent" in volume:
            has_local_persistent_volume = True
            volume["persistent"].setdefault("constraints", [])
            volume["persistent"].setdefault("type", "root")
    if has_local_persistent_volume:
        residency = local_definition.setdefault("residency", dict())
        residency.setdefault("relaunchEscalationTimeoutSeconds", 3600)
        residency.setdefault("taskLostBehavior", "WAIT_FOREVER")

    return local_definition, remote_definition


__config__ = MarathonApp
__manager__ = MarathonAppsManager
__config_name__ = "app"
