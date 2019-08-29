import json
from dcosdeploy.base import ConfigurationException
from dcosdeploy.adapters.metronome import MetronomeAdapter
from dcosdeploy.util import compare_dicts, print_if, update_dict_with_defaults


class MetronomeJob(object):
    def __init__(self, name, job_id, job_definition):
        self.name = name
        self.job_id = job_id
        self.job_definition = job_definition


def parse_config(name, config, config_helper):
    path = config.get("path", None)
    job_definition_path = config.get("definition")
    if not job_definition_path:
        raise ConfigurationException("Job %s has no definition file" % name)
    job_definition_path = config_helper.render(job_definition_path)

    job_definition = config_helper.read_file(job_definition_path)
    job_definition = config_helper.render(job_definition)
    job_definition = json.loads(job_definition)
    if path:
        path = config_helper.render(path)
    else:
        path = "/"+job_definition["id"].replace(".", "/")
    return MetronomeJob(name, path, job_definition)


class JobsManager(object):
    def __init__(self):
        self.api = MetronomeAdapter()

    def deploy(self, config, dependencies_changed=False, silent=False):
        if self.api.does_job_exist(config.job_id):
            print_if(not silent, "\tUpdating existing job")
            self.api.update_job(config.job_definition)
            print_if(not silent, "\tUpdated job.")
            return True
        else:
            print_if(not silent, "\tCreating job")
            self.api.create_job(config.job_definition)
            print_if(not silent, "\tCreated job.")
            return True

    def dry_run(self, config, dependencies_changed=False, debug=False):
        if not self.api.does_job_exist(config.job_id):
            print("Would create job %s" % config.job_id)
            return True
        existing_job_definition = self.api.get_job(config.job_id)
        diff = self._compare_job_definitions(config.job_definition, existing_job_definition)
        if diff:
            if debug:
                print("Would update job %s:" % config.job_id)
                print(diff)
            else:
                print("Would update job %s" % config.job_id)
        return diff is not None

    def delete(self, config, silent=False):
        print("\tDeleting job")
        deleted = self.api.delete_job(config.job_id)
        print("\tDeleted job.")
        return deleted

    def dry_delete(self, config):
        if self.api.does_job_exist(config.job_id):
            print("Would delete job %s" % config.job_id)
            return True
        else:
            return False


    def _compare_job_definitions(self, local_definition, remote_definition):
        local_definition, remote_definition = _normalize_definitions(local_definition, remote_definition)
        if "schedules" in remote_definition:
            for schedule in remote_definition["schedules"]:
                if "nextRunAt" in schedule:
                    del schedule["nextRunAt"]
        return compare_dicts(remote_definition, local_definition)


_job_defaults = dict(
    labels=dict(),
    schedules=list(),
)

_run_defaults = dict(
    artifacts=[],
    cmd="",
    disk=0,
    placement=dict(constraints=[]),
    volumes=list(),
)

_docker_defaults = dict(
    forcePullImage=False,
    parameters=[],
    privileged=False
)

_ucr_defaults = dict(
    privileged=False,
    image=dict(forcePull=False, kind="docker")
)


def _normalize_definitions(local_definition, remote_definition):
    update_dict_with_defaults(local_definition, _job_defaults)
    local_run = local_definition["run"]
    update_dict_with_defaults(local_run, _run_defaults)
    if "docker" in local_run:
        update_dict_with_defaults(local_run["docker"], _docker_defaults)
    if "ucr" in local_run:
        update_dict_with_defaults(local_run["ucr"], _ucr_defaults)
    if "gpus" in remote_definition["run"] and "gpus" not in local_run:
        local_run["gpus"] = 0
    for schedule in local_definition.get("schedules", list()):
        if "concurrencyPolicy" not in schedule:
            schedule["concurrencyPolicy"] = "ALLOW"
    return local_definition, remote_definition


__config__ = MetronomeJob
__manager__ = JobsManager
__config_name__ = "job"
