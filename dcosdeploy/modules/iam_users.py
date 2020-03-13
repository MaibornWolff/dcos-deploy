import json
from ..base import ConfigurationException
from ..util import global_config
from ..util.output import echo
from ..adapters.bouncer import BouncerAdapter


class IAMUser(object):
    def __init__(self, name, password, update_password, description, provider_type, provider_id, groups, permissions):
        self.name = name
        self.password = password
        self.update_password = update_password
        self.description = description
        self.provider_type = provider_type
        self.provider_id = provider_id
        self.groups = groups
        self.permissions = permissions


def render_permissions(config_helper, permissions):
    result = dict()
    for rid, actions in permissions.items():
        rid = config_helper.render(rid)
        actions = list(map(lambda action: config_helper.render(action), actions))
        result[rid] = actions
    return result


def parse_config(name, config, config_helper):
    name = config.get("name")
    if not name:
        raise ConfigurationException("name is required for iam_user")
    name = config_helper.render(name)
    description = config.get("description")
    if not description:
        raise ConfigurationException("description is required for iam_user")
    description = config_helper.render(description)
    password = config.get("password")
    if not password:
        raise ConfigurationException("password is required for iam_user")
    password = config_helper.render(password)
    update_password = config.get("update_password", True)
    provider_type = config_helper.render(config.get("provider_type"))
    provider_id = config_helper.render(config.get("provider_id"))
    groups = config.get("groups", list())
    permissions = render_permissions(config_helper, config.get("permissions", dict()))
    groups = [config_helper.render(g) for g in groups]
    return IAMUser(name, password, update_password, description, provider_type, provider_id, groups, permissions)


class IamUserBaseManager:
    def __init__(self):
        self.bouncer = BouncerAdapter()

    def _update_groups_permissions(self, name, groups, permissions):
        changed = False
        existing_groups = self.bouncer.get_groups_for_user(name)
        existing_permissions = self.bouncer.get_permissions_for_user(name)
        existing_rids = self.bouncer.get_rids()
        echo("\tUpdating groups")
        # Update groups
        for group in existing_groups:
            if group not in groups:
                self.bouncer.remove_user_from_group(name, group)
                changed = True
        for group in groups:
            if group not in existing_groups:
                self.bouncer.add_user_to_group(name, group)
                changed = True

        # Update permissions
        echo("\tUpdating permissions")
        for rid, actions in existing_permissions.items():
            target_actions = permissions.get(rid, list())
            for action in actions:
                if action not in target_actions:
                    self.bouncer.remove_permission_from_user(name, rid, action)
                    changed = True
        for rid, actions in permissions.items():
            if rid not in existing_rids:
                self.bouncer.create_permission(rid)
            for action in actions:
                if action not in existing_permissions.get(rid, list()):
                    self.bouncer.add_permission_to_user(name, rid, action)
                    changed = True
        return changed

    def _check_groups_permissions(self, name, groups, permissions):
        existing_rids = self.bouncer.get_rids()
        existing_groups = self.bouncer.get_groups_for_user(name)
        existing_permissions = self.bouncer.get_permissions_for_user(name)
        changes = False
        for rid, _ in permissions.items():
            if rid not in existing_rids:
                echo("Would create permission %s" % rid)
                changes = True
        # Check groups
        for group in existing_groups:
            if group not in groups:
                echo("Would remove user %s from group %s" % (name, group))
                changes = True
        for group in groups:
            if group not in existing_groups:
                echo("Would add user %s to group %s" % (name, group))
                changes = True
        # Check permissions
        for rid, actions in existing_permissions.items():
            if rid not in permissions:
                echo("Would remove permission %s completely from user %s" % (rid, name))
                changes = True
            else:
                for action in actions:
                    if action not in permissions[rid]:
                        echo("Would remove permission %s %s from user %s" % (rid, action, name))
                        changes = True
        for rid, actions in permissions.items():
            if rid not in existing_rids:
                echo("Would create permission %s" % rid)
            for action in actions:
                if action not in existing_permissions.get(rid, list()):
                    echo("Would add permission %s %s to user %s" % (rid, action, name))
                    changes = True
        return changes


class IAMUsersManager(IamUserBaseManager):
    def __init__(self):
        self.bouncer = BouncerAdapter()

    def deploy(self, config, dependencies_changed=False, force=False):
        changed = False
        existing_user = self.bouncer.get_account(config.name)
        if existing_user is None:
            echo("\tCreating user")
            self.bouncer.create_user(config.name, config.password, config.description, config.provider_type, config.provider_id)
            changed = True
        else:
            if config.update_password or existing_user["description"] != config.description:
                echo("\tUser already exists. Updating it.")
                self.bouncer.update_user(config.name, config.password if config.update_password else None, config.description)
            else:
                echo("\tUser already exists. Not updating it.")
        if self._update_groups_permissions(config.name, config.groups, config.permissions):
            changed = True
        return changed

    def dry_run(self, config, dependencies_changed=False):
        existing_user = self.bouncer.get_account(config.name)
        changed = False
        if existing_user is None:
            echo("Would create user %s" % config.name)
            return True
        else:
            if config.update_password:
                echo("Would update password for user %s" % config.name)
                changed = True
            if existing_user["description"] != config.description:
                if global_config.debug:
                    echo("Would update description for user %s from '%s' to '%s'" % (config.name, existing_user["description"], config.description))
                else:
                    echo("Would update description for user %s" % config.name)
                changed = True
        if self._check_groups_permissions(config.name, config.groups, config.permissions):
            changed = True
        return changed

    def delete(self, config, force=False):
        echo("\tDeleting user")
        self.bouncer.delete_account(config.name)
        echo("\tDeletion complete.")
        return True

    def dry_delete(self, config):
        if self.bouncer.get_account(config.name) is not None:
            echo("Would delete user %s" % config.name)
            return True
        else:
            return False


__config__ = IAMUser
__manager__ = IAMUsersManager
__config_name__ = "iam_user"
