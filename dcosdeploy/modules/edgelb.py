import time
from dcosdeploy.adapters.edgelb import EdgeLbAdapter
from dcosdeploy.base import ConfigurationException
from dcosdeploy.util import print_if


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
            # TODO: Check for changes
            print_if(not silent, "\tUpdating pool")
            self.api.update_pool(config.pool_config)
            print_if(not silent, "\tPool updated.")
            return True
        else:
            print_if(not silent, "\tCreating pool")
            self.api.create_pool(config.pool_config)
            print_if(not silent, "\tPool created.")
            return True

    def dry_run(self, config, dependencies_changed=False, print_changes=True, debug=False):
        if not self.api.ping():
            print("Would create pool %s" % config.name)
            return True
        exists = config.name in self.api.get_pools()
        if not exists:
            print("Would create pool %s" % config.name)
        print("Would possibly update pool %s" % config.name)
        return True


__config__ = EdgeLbPool
__manager__ = EdgeLbPoolsManager
__config_name__ = "edgelb"
