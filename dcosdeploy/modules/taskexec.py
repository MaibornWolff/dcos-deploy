from dcosdeploy.adapters.mesos import MesosAdapter
from dcosdeploy.base import ConfigurationException
from dcosdeploy.util import print_if


class TaskExec(object):
    def __init__(self, task, command, print_output):
        self.task = task
        self.command = command
        self.print_output = print_output


def parse_config(name, config, config_helper):
    task = config.get("task")
    if not task:
        raise ConfigurationException("task is required for taskexec '%s'" % name)
    command = config.get("command")
    if not command:
        raise ConfigurationException("command is required for taskexec '%s'" % name)
    print_output = config.get("print", False)
    task = config_helper.render(task)
    command = config_helper.render(command)
    return TaskExec(task, command, print_output)


class TaskExecManager(object):
    def __init__(self):
        self.api = MesosAdapter()

    def deploy(self, config, dependencies_changed=False, silent=False):
        print_if(not silent, "\tRunning command")
        parent_container_id, slave_id = self.api.get_container_id_and_slave_id_for_task(config.task)
        result = self.api.launch_nested_container(slave_id, parent_container_id, config.command.split(" "))
        if config.print_output and not silent:
            print(result)
        print_if(not silent, "\tFinished.")
        return True

    def dry_run(self, config, dependencies_changed=False, print_changes=True, debug=False):
        print("Would run command '%s' in task '%s'" % (config.command, config.task))
        return True


__config__ = TaskExec
__manager__ = TaskExecManager
__config_name__ = "taskexec"
