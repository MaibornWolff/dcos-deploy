import subprocess
import os
import json
from dcosdeploy.base import ConfigurationException
from dcosdeploy.adapters.bouncer import BouncerAdapter
from dcosdeploy.adapters.secrets import SecretsAdapter


PRIVATE_KEY = "private-key.pem"
PUBLIC_KEY = "public-key.pem"
LOGIN_ENDPOINT = "https://leader.mesos/acs/api/v1/auth/login"


class ServiceAccount(object):
    def __init__(self, name, path, secret, groups, permissions):
        self.name = name
        self.path = path
        self.secret = secret
        self.groups = groups
        self.permissions = permissions
        self.dependencies = list()

    def full_path(self):
        return "serviceaccount:"+self.name


def parse_config(name, config, variables):
    path = config.get("name")
    if not path:
        raise ConfigurationException("name is required for serviceaccounts")
    secret_path = config.get("secret")
    path = variables.render(path)
    secret_path = variables.render(secret_path)
    groups = config.get("groups", list())
    permissions = config.get("permissions", dict())
    groups = [variables.render(g) for g in groups]
    return ServiceAccount(name, path, secret_path, groups, permissions)


def generate_keypair():
    res = subprocess.run("dcos security org service-accounts keypair private-key.pem public-key.pem".split(" "), shell=False)
    if res.returncode != 0:
        os.remove(PRIVATE_KEY)
        os.remove(PUBLIC_KEY)
        raise Exception("Error when creating keypair: %s" % res.stderr)
    with open(PRIVATE_KEY) as private_file:
        private_key = private_file.read()
    with open(PUBLIC_KEY) as public_file:
        public_key = public_file.read()
    os.remove(PRIVATE_KEY)
    os.remove(PUBLIC_KEY)
    return private_key, public_key


class AccountsManager(object):
    def __init__(self):
        self.bouncer = BouncerAdapter()
        self.secrets = SecretsAdapter()

    def does_serviceaccount_exist(self, path):
        return self.bouncer.get_account(path) is not None

    def create_serviceaccount(self, path, secret):
        private_key, public_key = generate_keypair()
        self.bouncer.create_account(path, "", public_key)
        ca_secret = json.dumps(dict(login_endpoint=LOGIN_ENDPOINT, private_key=private_key, scheme="RS256", uid=path))
        self.secrets.write_secret(secret, ca_secret, update=False)

    def deploy(self, config, dependencies_changed=False):
        changed = False
        if not self.does_serviceaccount_exist(config.path):
            print("\tCreating serviceaccount")
            self.create_serviceaccount(config.path, config.secret)
            changed = True
        else:
            print("\tServiceaccount already exists. Not creating it.")
        existing_groups = self.bouncer.get_groups_for_user(config.path)
        existing_permissions = self.bouncer.get_permissions_for_user(config.path)
        print("\tUpdating groups")
        # Update groups
        for group in existing_groups:
            if group not in config.groups:
                self.bouncer.remove_user_from_group(config.path, group)
                changed = True
        for group in config.groups:
            if group not in existing_groups:
                self.bouncer.add_user_to_group(config.path, group)
                changed = True
        # Update permissions
        print("\tUpdating permissions")
        for rid, actions in existing_permissions.items():
            if rid not in config.permissions:
                self.bouncer.remove_permission_from_user(config.path, rid)
                changed = True
            else:
                for action in actions:
                    if action not in config.permissions[rid]:
                        self.bouncer.remove_permission_from_user(config.path, rid, action)
                        changed = True
        for rid, actions in config.permissions.items():
            for action in actions:
                if action not in existing_permissions.get(rid, list()):
                    self.bouncer.add_permission_to_user(config.path, rid, action)
                    changed = True
        return changed

    def dry_run(self, config, dependencies_changed=False, debug=False):
        if not self.does_serviceaccount_exist(config.path):
            print("Would create serviceaccount %s" % config.path)
            return True
        existing_groups = self.bouncer.get_groups_for_user(config.path)
        existing_permissions = self.bouncer.get_permissions_for_user(config.path)

        changes = False
        # Check groups
        for group in existing_groups:
            if group not in config.groups:
                print("Would remove user %s from group %s" % (config.path, group))
                changes = True
        for group in config.groups:
            if group not in existing_groups:
                print("Would add user %s to group %s" % (config.path, group))
                changes = True
        # Check permissions
        for rid, actions in existing_permissions.items():
            if rid not in config.permissions:
                print("Would remove permission %s completely from user %s" % (rid, config.path))
                changes = True
            else:
                for action in actions:
                    if action not in config.permissions[rid]:
                        print("Would remove permission %s %s from user %s" % (rid, action, config.path))
                        changes = True
        for rid, actions in config.permissions.items():
            for action in actions:
                if action not in existing_permissions.get(rid, list()):
                    print("Would add permission %s %s to user %s" % (rid, action, config.path))
                    changes = True
        return changes


__config__ = ServiceAccount
__manager__ = AccountsManager
__config_name__ = "serviceaccount"
