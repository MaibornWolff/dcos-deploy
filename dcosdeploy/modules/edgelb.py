import time
from ..adapters.edgelb import EdgeLbAdapter
from ..base import ConfigurationException
from ..util import compare_dicts, update_dict_with_defaults
from ..util.output import echo, echo_diff


class EdgeLbPool(object):
    def __init__(self, api_server, name, pool_config):
        self.api_server = api_server
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
    api_server = config.get("api_server")
    if not api_server:
        api_server = "edgelb"
    api_server = config_helper.render(api_server)
    if api_server[-1] == "/":
        api_server = api_server[:-1]
    if not api_server.endswith("/api"):
        api_server = api_server + "/api"
    if api_server[0] == "/":
        api_server = api_server[1:]
    return EdgeLbPool(api_server, name, pool_config)


class EdgeLbPoolsManager(object):
    def __init__(self):
        self.api = EdgeLbAdapter()

    def deploy(self, config, dependencies_changed=False, force=False):
        if not self.api.ping(config.api_server):
            echo("\tEdgeLB api not yet available. Waiting ...")
            waiting = 0
            while not self.api.ping(config.api_server):
                time.sleep(10)
                waiting += 1
                if waiting > 12:
                    echo("\tCould not reach edgelb api. Giving up")
                    raise Exception("EdgeLB api not available.")
        exists = config.name in self.api.get_pools(config.api_server)
        if exists:
            echo("\tUpdating pool")
            self.api.update_pool(config.api_server, config.pool_config)
            echo("\tPool updated.")
            return True
        else:
            echo("\tCreating pool")
            self.api.create_pool(config.api_server, config.pool_config)
            echo("\tPool created.")
            return True

    def dry_run(self, config, dependencies_changed=False):
        if not self.api.ping(config.api_server):
            echo("Could not reach api-server. Would probably create pool %s" % config.name)
            return True
        exists = config.name in self.api.get_pools(config.api_server)
        if not exists:
            echo("Would create pool %s" % config.name)
            return True
        existing_pool_config = self.api.get_pool(config.api_server, config.name)
        local_pool_config, existing_pool_config = _normalize_pool_definition(config.pool_config, existing_pool_config)
        diff = compare_dicts(existing_pool_config, local_pool_config)
        if diff:
            echo_diff("Would update pool %s" % config.name, diff)
            return True
        else:
            return False

    def delete(self, config, force=False):
        echo("\tDeleting pool")
        deleted = self.api.delete_pool(config.api_server, config.name)
        echo("\tDeleted pool.")
        return deleted

    def dry_delete(self, config):
        if config.name in self.api.get_pools(config.api_server):
            echo("Would delete pool %s" % config.name)
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
    haproxy=dict(stats=dict(bindAddress="0.0.0.0")),
    type="static",
    secrets=[],
)

# New parameters introduced in version 1.2.3
_pool_defaults_123 = dict(
    poolHealthcheckGracePeriod=180,
    poolHealthcheckInterval=12,
    poolHealthcheckMaxFail=5,
    poolHealthcheckTimeout=60
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
    if "namespace" in remote_pool_config and "namespace" not in local_pool_config:
        local_pool_config["namespace"] = remote_pool_config["namespace"]
    # Apply default values on top level
    update_dict_with_defaults(local_pool_config, _pool_defaults)
    # Detect if new parameters introduced in v1.2.3 are present in remote config and add their defaults to the local config to avoid false positives
    if "poolHealthcheckGracePeriod" in remote_pool_config:
        update_dict_with_defaults(local_pool_config, _pool_defaults_123)


    local_haproxy = local_pool_config["haproxy"]
    # Normalize backends
    for backend in local_haproxy["backends"]:
        update_dict_with_defaults(backend, _backend_defaults)
        for service in backend["services"]:
            update_dict_with_defaults(service, _service_defaults)
    for frontend in local_haproxy["frontends"]:
        update_dict_with_defaults(frontend, _frontend_defaults)
        if "name" not in frontend:
            frontend["name"] = "frontend_{}_{}".format(frontend["bindAddress"], frontend["bindPort"])
    return local_pool_config, remote_pool_config


__config__ = EdgeLbPool
__manager__ = EdgeLbPoolsManager
__config_name__ = "edgelb"
