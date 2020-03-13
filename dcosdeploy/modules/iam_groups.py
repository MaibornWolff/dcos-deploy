import json
from ..base import ConfigurationException
from ..util import global_config
from ..util.output import echo
from ..adapters.bouncer import BouncerAdapter
from .iam_users import render_permissions


class IAMGroup(object):
    def __init__(self, name, description, provider_type, permissions):
        self.name = name
        self.description = description
        self.provider_type = provider_type
        self.permissions = permissions


def parse_config(name, config, config_helper):
    name = config.get("name")
    if not name:
        raise ConfigurationException("name is required for iam_group")
    name = config_helper.render(name)
    description = config.get("description")
    if not description:
        raise ConfigurationException("description is required for iam_group")
    description = config_helper.render(description)
    provider_type = config_helper.render(config.get("provider_type"))
    permissions = render_permissions(config_helper, config.get("permissions", dict()))
    return IAMGroup(name, description, provider_type, permissions)


class IAMGroupsManager:
    def __init__(self):
        self.bouncer = BouncerAdapter()

    def deploy(self, config, dependencies_changed=False, force=False):
        changed = False
        existing_group = self.bouncer.get_group(config.name)
        if existing_group is None:
            echo("\tCreating group")
            self.bouncer.create_group(config.name, config.description, config.provider_type)
            changed = True
        else:
            if existing_group["description"] != config.description:
                echo("\tGroup already exists. Updating description.")
                self.bouncer.update_group(config.name, config.description)
            else:
                echo("\tGroup already exists.")
        existing_permissions = self.bouncer.get_permissions_for_group(config.name)
        existing_rids = self.bouncer.get_rids()
        # Update permissions
        echo("\tUpdating permissions")
        for rid, actions in existing_permissions.items():
            target_actions = config.permissions.get(rid, list())
            for action in actions:
                if action not in target_actions:
                    self.bouncer.remove_permission_from_group(config.name, rid, action)
                    changed = True
        for rid, actions in config.permissions.items():
            if rid not in existing_rids:
                self.bouncer.create_permission(rid)
            for action in actions:
                if action not in existing_permissions.get(rid, list()):
                    self.bouncer.add_permission_to_group(config.name, rid, action)
                    changed = True
        return changed

    def dry_run(self, config, dependencies_changed=False):
        existing_group = self.bouncer.get_group(config.name)
        if existing_group is None:
            echo("Would create group %s" % config.name)
            return True
        elif existing_group["description"] != config.description:
            if global_config.debug:
                echo("Would update description for group %s from '%s' to '%s'" % (config.name, existing_group["description"], config.description))
            else:
                echo("Would update description for group %s" % config.name)

        # Check permissions
        existing_rids = self.bouncer.get_rids()
        existing_permissions = self.bouncer.get_permissions_for_group(config.name)
        changes = False
        for rid, actions in existing_permissions.items():
            if rid not in config.permissions:
                echo("Would remove permission %s completely from group %s" % (rid, config.name))
                changes = True
            else:
                for action in actions:
                    if action not in config.permissions[rid]:
                        echo("Would remove permission %s %s from group %s" % (rid, action, config.name))
                        changes = True
        for rid, actions in config.permissions.items():
            if rid not in existing_rids:
                echo("Would create permission %s" % rid)
            for action in actions:
                if action not in existing_permissions.get(rid, list()):
                    echo("Would add permission %s %s to group %s" % (rid, action, config.name))
                    changes = True
        return changes

    def delete(self, config, force=False):
        echo("\tDeleting group")
        self.bouncer.delete_group(config.name)
        echo("\tDeletion complete.")
        return True

    def dry_delete(self, config):
        if self.bouncer.get_group(config.name) is not None:
            echo("Would delete group %s" % config.name)
            return True
        else:
            return False


__config__ = IAMGroup
__manager__ = IAMGroupsManager
__config_name__ = "iam_group"
