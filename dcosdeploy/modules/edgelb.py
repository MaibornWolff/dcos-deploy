import time
from ..adapters.edgelb import EdgeLbAdapter
from ..base import ConfigurationException
from ..util import compare_dicts, update_dict_with_defaults, compare_text
from ..util.output import echo, echo_diff
BASIC_AUTH_ANCHOR="<%|BASIC_AUTH_ANCHOR|%>"

class EdgeLbPool:
    def __init__(self, api_server, name, pool_config, pool_template, basic_auth):
        self.api_server = api_server
        self.name = name
        self.pool_config = pool_config
        self.pool_template = pool_template
        self.basic_auth = basic_auth


def create_password_hash(password):
    pass


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
        raise ConfigurationException(
            "Unknown file type for Edge-LB pool config file: '%s'. Must backend json or yaml" % pool_filepath)

    template_filepath = config.get("template")
    if template_filepath:
        template_filepath = config_helper.render(template_filepath)
        pool_template = config_helper.read_file(template_filepath)
    basic_auth = config.get("basic_auth")
    if basic_auth:
        if not template_filepath:
            raise ConfigurationException(f'You need to provide a haproxy pool template and place the anchor with the value {BASIC_AUTH_ANCHOR}\n'
                                         f'where the basic auth config for haproxy should be pasted.')
        generate_basic_auth_config(basic_auth, config_helper, pool_config, template_filepath)

    else:
        pool_template = None

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

    return EdgeLbPool(api_server, name, pool_config, pool_template)


def generate_basic_auth_config(basic_auth, config_helper, pool_config, template_filepath):
    basic_auth = config_helper.render(basic_auth)
    haproxy_basic_auth_lists = ""
    for backend_name, userlist in basic_auth.items():
        userlist_entry = f"userlist {backend_name}-userlist\n"
        for entry in userlist:
            user = entry.get('user')
            password_hash = create_password_hash(entry.get('password'))
            entry = f"  user {user} password {password_hash}\n"
            userlist_entry += entry
        userlist_entry += "\n"
        haproxy_basic_auth_lists += userlist_entry
        concerned_backend = [backend for backend in pool_config["haproxy"]["backends"] if backend.get("name ") == backend_name][0]
        string_params = concerned_backend.get("miscStrs", [])
        string_params.append(f"acl user-allowed http_auth({backend_name}-userlist)")
        string_params.append("http-request auth realm allowed-users unless user-allowed")
        concerned_backend["miscStrs"] = string_params
    template_filepath.replace(BASIC_AUTH_ANCHOR, haproxy_basic_auth_lists)


class EdgeLbPoolsManager:
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
        pool_exists = config.name in self.api.get_pools(config.api_server)
        if pool_exists:
            echo("\tUpdating pool")
            self.api.update_pool(config.api_server, config.pool_config)
            echo("\tPool updated.")
            pool_created = True
        else:
            echo("\tCreating pool")
            self.api.create_pool(config.api_server, config.pool_config)
            echo("\tPool created.")
            pool_created = True

        if config.pool_template:
            echo("\tUpdating pool template.")
            self.api.update_pool_template(config.api_server, config.name, config.pool_template)
            echo("\tPool template updated")
            return True
        else:
            return pool_created

    def dry_run(self, config, dependencies_changed=False):
        if not self.api.ping(config.api_server):
            echo("Could not reach api-server. Would probably create pool %s" % config.name)
            return True
        pool_exists = config.name in self.api.get_pools(config.api_server)
        if not pool_exists:
            echo("Would create pool %s" % config.name)
            pool_updated = True

        existing_pool_config = self.api.get_pool(config.api_server, config.name)
        local_pool_config, existing_pool_config = _normalize_pool_definition(config.pool_config, existing_pool_config)
        pool_diff = compare_dicts(existing_pool_config, local_pool_config)
        if pool_diff:
            echo_diff("Would update pool %s" % config.name, pool_diff)
            pool_updated = True
        else:
            pool_updated = False
        if config.pool_template:
            remote_pool_template = self.api.get_pool_template(config.api_server, config.name)
            remote_pool_template = remote_pool_template.replace(r'\n', '\n')
            template_diff = compare_text(remote_pool_template.strip(), config.pool_template.strip())
            if template_diff:
                template_updated = True
                echo_diff("Would update template for pool %s" % config.name, template_diff)
            else:
                template_updated = False
        else:
            template_updated = False
        return pool_updated or template_updated

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

_backend_defaults = dict(
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

    # Normalize frontends
    for frontend in local_haproxy["frontends"]:
        if "linkBackend" not in frontend:
            frontend["linkBackend"] = dict(map=list())
        elif "linkBackend" in frontend and "map" not in frontend["linkBackend"]:
            frontend["linkBackend"]["map"] = list()
    return local_pool_config, remote_pool_config


__config__ = EdgeLbPool
__manager__ = EdgeLbPoolsManager
__config_name__ = "edgelb"
