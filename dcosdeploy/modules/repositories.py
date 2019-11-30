from dcosdeploy.base import ConfigurationException
from dcosdeploy.util import print_if
from dcosdeploy.adapters.cosmos import CosmosAdapter


class PackageRepository(object):
    def __init__(self, name, uri, index):
        self.name = name
        self.uri = uri
        self.index = index


def parse_config(name, config, config_helper):
    repo_name = config.get("name", name)
    repo_uri = config.get("uri")
    if not repo_uri:
        raise ConfigurationException("repositroy %s has no uri field" % name)
    repo_index = config.get("index", None)
    repo_name = config_helper.render(repo_name)
    repo_uri = config_helper.render(repo_uri)
    return PackageRepository(repo_name, repo_uri, repo_index)


class PackageRepositoriesManager(object):
    def __init__(self):
        self.api = CosmosAdapter()

    def deploy(self, config, dependencies_changed=False, silent=False, force=False):
        repo = self._get_repo(config.name)
        if repo:
            if repo["uri"] != config.uri:
                print_if(not silent, "\tURIs do not match. Deleting old repository")
                self.api.delete_repository(config.name)
            else:
                print_if(not silent, "\tNothing changed.")
                return False
        print_if(not silent, "\tAdding repository")
        self.api.add_repository(config.name, config.uri, config.index)
        print_if(not silent, "\tFinished")
        return True

    def dry_run(self, config, dependencies_changed=False, debug=False):
        repo = self._get_repo(config.name)
        if not repo:
            print("Would add repository %s" % config.name)
            return True
        elif repo["uri"] != config.uri:
            if debug:
                print("Would change URI of repository %s from %s to %s" % (config.name, repo["uri"], config.uri))
            else:
                print("Would change URI of repository %s" % config.name)
            return True
        else:
            return False

    def delete(self, config, silent=False, force=False):
        print("\tDeleting repository")
        deleted = self.api.delete_repository(config.name)
        print("\tDeleted repository.")
        return deleted

    def dry_delete(self, config):
        if self._get_repo(config.name):
            print("Would delete repository %s" % config.name)
            return True
        else:
            return False

    def _get_repo(self, name):
        repo_list = self.api.list_repositories()
        for repo in repo_list:
            if repo["name"] == name:
                return repo
        return None


__config__ = PackageRepository
__manager__ = PackageRepositoriesManager
__config_name__ = "repository"
