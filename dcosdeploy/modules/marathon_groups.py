from ..base import ConfigurationException
from ..util.output import echo
from ..adapters.marathon import MarathonAdapter
from ..adapters.mesos import MesosAdapter


class MarathonGroup:
    def __init__(self, name, quota, enforce_role):
        self.name = name
        self.quota = quota
        self.enforce_role = enforce_role


class GroupQuota:
    def __init__(self, cpus, mem, disk, gpus):
        self.cpus = cpus
        self.mem = mem
        self.disk = disk
        self.gpus = gpus


def _parse_quota(config, config_helper):
    cpus = float(config_helper.render(str(config.get("cpus", 0))))
    mem = float(config_helper.render(str(config.get("mem", 0))))
    disk = float(config_helper.render(str(config.get("disk", 0))))
    gpus = float(config_helper.render(str(config.get("gpus", 0))))
    return GroupQuota(cpus, mem, disk, gpus)


def parse_config(name, config, config_helper):
    group_name = config.get("name", name)
    if not group_name:
        raise ConfigurationException("marathon_group needs a field name")
    group_name = config_helper.render(group_name)
    if group_name[0] == "/":
        group_name = group_name[1:]
    enforce_role = config.get("enforce_role", False)
    quota_config = config.get("quota")
    if group_name.count("/") > 0 and quota_config:
        raise ConfigurationException("Only top-level groups can have quotas: %s" % group_name)
    quota = _parse_quota(quota_config, config_helper) if quota_config else None
    return MarathonGroup(group_name, quota, enforce_role)


class MarathonGroupsManager:
    def __init__(self):
        self.marathon_api = MarathonAdapter()
        self.mesos_api = MesosAdapter()

    def deploy(self, config, dependencies_changed=False, force=False):
        group = self.marathon_api.get_group(config.name)
        if group:
            if group["enforceRole"] != config.enforce_role:
                echo("\tUpdating enforce_role")
                self.marathon_api.update_group(config.name, config.enforce_role)
            if config.quota and self._quota_changed(config.name, config.quota):
                echo("\tUpdating quota")
                self.mesos_api.update_quota(config.name, config.quota, config.enforce_role)
        else:
            echo("\tCreating marathon group")
            self.marathon_api.add_group(config.name, config.enforce_role)
            if config.quota:
                echo("\tSetting quota")
                self.mesos_api.update_quota(config.name, config.quota)

        echo("\tFinished")
        return True

    def dry_run(self, config, dependencies_changed=False):
        group = self.marathon_api.get_group(config.name)
        changes = False
        if group:
            if config.enforce_role != group["enforceRole"]:
                echo("Would set enforce_role of %s to %s" % (config.name, config.enforce_role))
                changes = True
            if config.quota and self._quota_changed(config.name, config.quota):
                echo("Would update quota of %s" % config.name)
                changes = True
        else:
            echo("Would create marathon group %s" % config.name)
            changes = True
        return changes

    def delete(self, config, force=False):
        echo("\tDeleting marathon group %s" % config.name)
        deleted = self.marathon_api.delete_group(config.name)
        echo("\tDeleted marathon group.")
        return deleted

    def dry_delete(self, config):
        if self.marathon_api.get_group(config.name):
            echo("Would delete marathon group %s" % config.name)
            return True
        else:
            return False

    def _quota_changed(self, name, new_quota):
        quota = self.mesos_api.get_quota(name)
        if quota:
            limit = quota["limit"]
            return not (limit.get("cpus", 0) == new_quota.cpus and limit.get("mem", 0) == new_quota.mem and limit.get("disk", 0) == new_quota.disk and limit.get("gpus", 0) == new_quota.gpus)
        else:
            return True


__config__ = MarathonGroup
__manager__ = MarathonGroupsManager
__config_name__ = "marathon_group"
