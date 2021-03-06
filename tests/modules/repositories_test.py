import unittest
from unittest import mock
from dcosdeploy.config import VariableContainer
from dcosdeploy.util import global_config


global_config.silent = True


REPOSITORY_CONFIG = dict(type="repository", name="foo", uri="http://bar")
REPO_LIST = [dict(name="foo", uri="bar"), dict(name="universe", uri="dcos")]


@mock.patch("dcosdeploy.auth.get_base_url", lambda: "/bla")
class RepositoriesTest(unittest.TestCase):
    def test_parse_config(self):
        from dcosdeploy.modules.repositories import parse_config, PackageRepository
        variables = VariableContainer(dict())
        repo = parse_config("myrepo", REPOSITORY_CONFIG, variables)
        self.assertIsNotNone(repo)
        self.assertTrue(isinstance(repo, PackageRepository))
        self.assertEqual(repo.name, "foo")
        self.assertEqual(repo.uri, "http://bar")
        self.assertIsNone(repo.index)

    @mock.patch("dcosdeploy.modules.repositories.CosmosAdapter")
    def test_deploy_create_repo(self, mock_cosmosadapter):
        # given
        mock_cosmosadapter.return_value.list_repositories.side_effect = lambda: []
        # when
        from dcosdeploy.modules.repositories import PackageRepository, PackageRepositoriesManager
        repo = PackageRepository(name="foo", uri="bar", index=None)
        manager = PackageRepositoriesManager()
        result = manager.deploy(repo)
        # then
        self.assertTrue(result)
        mock_cosmosadapter.return_value.add_repository.assert_called_with("foo", "bar", None)
        mock_cosmosadapter.return_value.delete_repository.assert_not_called()

    @mock.patch("dcosdeploy.modules.repositories.CosmosAdapter")
    def test_deploy_recreate_repo(self, mock_cosmosadapter):
        # given
        mock_cosmosadapter.return_value.list_repositories.side_effect = lambda: REPO_LIST
        # when
        from dcosdeploy.modules.repositories import PackageRepository, PackageRepositoriesManager
        repo = PackageRepository(name="foo", uri="baz", index=None)
        manager = PackageRepositoriesManager()
        result = manager.deploy(repo)
        # then
        self.assertTrue(result)
        mock_cosmosadapter.return_value.delete_repository.assert_called_with("foo")
        mock_cosmosadapter.return_value.add_repository.assert_called_with("foo", "baz", None)

    @mock.patch("dcosdeploy.modules.repositories.CosmosAdapter")
    def test_dry_run(self, mock_cosmosadapter):
        mock_cosmosadapter.return_value.list_repositories.side_effect = lambda: REPO_LIST
        from dcosdeploy.modules.repositories import PackageRepository, PackageRepositoriesManager
        repo_exists = PackageRepository(name="foo", uri="bar", index=None)
        repo_notexists = PackageRepository(name="nada", uri="bar", index=None)
        repo_changed = PackageRepository(name="foo", uri="baz", index=None)
        manager = PackageRepositoriesManager()
        self.assertFalse(manager.dry_run(repo_exists))
        self.assertTrue(manager.dry_run(repo_changed))
        self.assertTrue(manager.dry_run(repo_notexists))

    @mock.patch("dcosdeploy.modules.repositories.CosmosAdapter")
    def test_dry_delete(self, mock_cosmosadapter):
        mock_cosmosadapter.return_value.list_repositories.side_effect = lambda: REPO_LIST
        from dcosdeploy.modules.repositories import PackageRepository, PackageRepositoriesManager
        repo_exists = PackageRepository(name="foo", uri="bar", index=None)
        repo_notexists = PackageRepository(name="nada", uri="bar", index=None)
        manager = PackageRepositoriesManager()
        self.assertTrue(manager.dry_delete(repo_exists))
        self.assertFalse(manager.dry_delete(repo_notexists))

    @mock.patch("dcosdeploy.modules.repositories.CosmosAdapter")
    def test_delete(self, mock_cosmosadapter):
        mock_cosmosadapter.return_value.delete_repository.side_effect = lambda name: name == "foo"
        from dcosdeploy.modules.repositories import PackageRepository, PackageRepositoriesManager
        repo_exists = PackageRepository(name="foo", uri="bar", index=None)
        repo_notexists = PackageRepository(name="nada", uri="bar", index=None)
        manager = PackageRepositoriesManager()
        self.assertTrue(manager.delete(repo_exists))
        self.assertFalse(manager.delete(repo_notexists))