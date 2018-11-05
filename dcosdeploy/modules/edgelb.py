import time
import yaml
import json
from dcosdeploy.adapters.edgelb import EdgeLbAdapter
from dcosdeploy.base import ConfigurationException


class EdgeLbPool(object):
    def __init__(self, name, pool_config):
        self.name = name
        self.pool_config = pool_config


def parse_config(name, config, variables):
    name = config.get("name")
    if name:
        name = variables.render(name)
    pool_filepath = config.get("pool")
    if not pool_filepath:
        raise ConfigurationException("Pool file is required for edgelb")
    pool_filepath = variables.render(pool_filepath)
    with open(pool_filepath) as pool_file:
        file_content = pool_file.read()
    file_content = variables.render(file_content)
    if pool_filepath.lower().endswith(".yml") or pool_filepath.lower().endswith(".yaml"):
        pool_config = yaml.load(file_content)
    elif pool_filepath.lower().endswith(".json"):
        pool_config = json.loads(file_content)
    else:
        raise ConfigurationException("Unknown file type for Edge-LB pool config file: '%s'. Must be json or yaml" % pool_filepath)
    if not name:
        name = pool_config["name"]
    return EdgeLbPool(name, pool_config)


class EdgeLbPoolsManager(object):
    def __init__(self):
        self.api = EdgeLbAdapter()

    def deploy(self, config, dependencies_changed=False):
        if not self.api.ping():
            print("\tEdgeLB api not yet available. Waiting ...")
            waiting = 0
            while not self.api.ping():
                time.sleep(10)
                waiting += 1
                if waiting > 12:
                    print("\tCould not reach edgelb api. Giving up")
                    raise Exception("EdgeLB api not available.")
        exists = config.name in self.api.get_pools()
        if exists:
            # TODO: Check for changes
            print("\tUpdating pool")
            self.api.update_pool(config.pool_config)
            print("\tPool updated.")
            return True
        else:
            print("\tCreating pool")
            self.api.create_pool(config.pool_config)
            print("\tPool created.")
            return True

    def dry_run(self, config, dependencies_changed=False, debug=False):
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
