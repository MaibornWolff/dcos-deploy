import time
from dcosdeploy.adapters.edgelb import EdgeLbAdapter
from dcosdeploy.base import ConfigurationException
from dcosdeploy.util import print_if, compare_dicts, update_dict_with_defaults


class EdgeLbPool(object):
    def __init__(self, name, pool_config):
        self.name = name
        self.pool_config = pool_config


def parse_config(name, config, config_helper):
    name = config.get("name")
    if name:
        name = config_helper.render(name)
    pool_filepath = config.get("pool")
    if not pool_filepath:
        raise ConfigurationException("Pool file is required for edgelb")
    pool_filepath = config_helper.render(pool_filepath)
    if pool_filepath.lower().endswith(".yml") or pool_filepath.lower().endswith(".yaml"):
        pool_config = config_helper.read_yaml(pool_filepath, render_variables=True)
    elif pool_filepath.lower().endswith(".json"):
        pool_config = config_helper.read_json(pool_filepath, render_variables=True)
    else:
        raise ConfigurationException("Unknown file type for Edge-LB pool config file: '%s'. Must be json or yaml" % pool_filepath)
    if not name:
        name = pool_config["name"]
    return EdgeLbPool(name, pool_config)


class EdgeLbPoolsManager(object):
    def __init__(self):
        self.api = EdgeLbAdapter()

    def deploy(self, config, dependencies_changed=False, silent=False):
        if not self.api.ping():
            print_if(not silent, "\tEdgeLB api not yet available. Waiting ...")
            waiting = 0
            while not self.api.ping():
                time.sleep(10)
                waiting += 1
                if waiting > 12:
                    print_if(not silent, "\tCould not reach edgelb api. Giving up")
                    raise Exception("EdgeLB api not available.")
        exists = config.name in self.api.get_pools()
        if exists:
            existing_pool_config = self.api.get_pool(config.name)
            local_pool_config, existing_pool_config = _normalize_pool_definition(config.pool_config, existing_pool_config)
            if not compare_dicts(local_pool_config, existing_pool_config):
                print_if(not silent, "\tUpdating pool")
                self.api.update_pool(config.pool_config)
                print_if(not silent, "\tPool updated.")
                return True
            else:
                print_if(not silent, "\tNothing changed")
                return False
        else:
            print_if(not silent, "\tCreating pool")
            self.api.create_pool(config.pool_config)
            print_if(not silent, "\tPool created.")
            return True

    def dry_run(self, config, dependencies_changed=False, print_changes=True, debug=False):
        if not self.api.ping():
            print("Could not reach api-server. Would probably create pool %s" % config.name)
            return True
        exists = config.name in self.api.get_pools()
        if not exists:
            print("Would create pool %s" % config.name)
            return True
        existing_pool_config = self.api.get_pool(config.name)
        local_pool_config, existing_pool_config = _normalize_pool_definition(config.pool_config, existing_pool_config)
        if not compare_dicts(local_pool_config, existing_pool_config, print_differences=debug):
            print("Would update pool %s" % config.name)
            return True
        else:
            return False


_pool_defaults = dict(
    constraints="hostname:UNIQUE",
    cpus=0.9,
    cpusAdminOverhead=0.1,
    disk=256,
    virtualNetworks=[],
    role="slave_public",
    ports=[],
    memAdminOverhead=32,
    mem=992,
    haproxy=dict(stats=dict(bindAddress="0.0.0.0"))
)

_backend_defaults= dict(
    balance="roundrobin",
    miscStrs=[],
    protocol="HTTP",
    rewriteHttp=dict(
        request=dict(
            forwardfor=True,
            rewritePath=True,
            setHostHeader=True,
            xForwardedPort=True,
            xForwardedProtoHttpsIfTls=True,
        ),
        response=dict(
            rewriteLocation=True
        )
    )
)

_service_defaults = dict(
    endpoint=dict(
        check=dict(
            enabled=True
        ),
        port=-1,
	    type="AUTO_IP"
    ),
    marathon={},
    mesos={}
)

_frontend_defaults = dict(
    bindAddress="0.0.0.0",
    certificates=[],
    miscStrs=[]
)


def _normalize_pool_definition(local_pool_config, remote_pool_config):
    # Remove meta values
    for key in ["packageVersion", "packageName"]:
        if key in local_pool_config:
            del local_pool_config[key]
        if key in remote_pool_config:
            del remote_pool_config[key]
    # Apply default values on top level
    update_dict_with_defaults(local_pool_config, _pool_defaults)

    local_haproxy = local_pool_config["haproxy"]
    # Normalize backends
    for backend in local_haproxy["backends"]:
        update_dict_with_defaults(backend, _backend_defaults)
        for service in backend["services"]:
            update_dict_with_defaults(service, _service_defaults)
    for frontend in local_haproxy["frontends"]:
        update_dict_with_defaults(frontend, _frontend_defaults)
    return local_pool_config, remote_pool_config


__config__ = EdgeLbPool
__manager__ = EdgeLbPoolsManager
__config_name__ = "edgelb"
