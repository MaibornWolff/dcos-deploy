import json
from ..base import ConfigurationException
from ..adapters.metronome import MetronomeAdapter
from ..util import compare_dicts, update_dict_with_defaults
from ..util.output import echo, echo_diff


class MetronomeJob(object):
    def __init__(self, name, job_id, job_definition, schedule_definition):
        self.name = name
        self.job_id = job_id
        self.job_definition = job_definition
        self.schedule_definition = schedule_definition


def parse_config(name, config, config_helper):
    path = config.get("path", None)
    job_definition_path = config.get("definition")
    if not job_definition_path:
        raise ConfigurationException("Job %s has no definition file" % name)
    job_definition_path = config_helper.render(job_definition_path)

    job_definition = config_helper.read_file(job_definition_path)
    job_definition = config_helper.render(job_definition)
    job_definition = json.loads(job_definition)
    schedule_definition = job_definition.get("schedule", None)
    job_definition = job_definition["job"]
    if path:
        path = config_helper.render(path)
        if path[0] == "/":
            path = path[1:]
    else:
        path = job_definition["id"]
    path = path.replace("/", ".")
    return MetronomeJob(name, path, job_definition, schedule_definition)


class JobsManager(object):
    def __init__(self):
        self.api = MetronomeAdapter()

    def deploy(self, config, dependencies_changed=False, force=False):
        if self.api.does_job_exist(config.job_id):
            echo("\tUpdating existing job")
            self.api.update_job(config.job_id, config.job_definition)
            self.api.update_schedule(config.job_id, config.schedule_definition)
            echo("\tUpdated job.")
            return True
        else:
            echo("\tCreating job")
            self.api.create_job(config.job_definition)
            self.api.create_schedule(config.job_id, config.schedule_definition)
            echo("\tCreated job.")
            return True

    def dry_run(self, config, dependencies_changed=False):
        if not self.api.does_job_exist(config.job_id):
            echo("Would create job %s" % config.job_id)
            return True
        existing_job_definition = self.api.get_job(config.job_id)
        existing_schedule_definition = self.api.get_schedules(config.job_id)
        job_diff = self._compare_job_definitions(config.job_definition, existing_job_definition)
        if job_diff:
            echo_diff("Would update job %s" % config.job_id, job_diff)
        schedule_diff = self._compare_schedule_definitions(config.schedule_definition, existing_schedule_definition)
        if schedule_diff:
            echo_diff("Would update schedule for job %s" % config.job_id, schedule_diff)
        return job_diff is not None or schedule_diff is not None

    def delete(self, config, force=False):
        echo("\tDeleting job")
        deleted = self.api.delete_job(config.job_id)
        echo("\tDeleted job.")
        return deleted

    def dry_delete(self, config):
        if self.api.does_job_exist(config.job_id):
            echo("Would delete job %s" % config.job_id)
            return True
        else:
            return False

    def _compare_job_definitions(self, local_definition, remote_definition):
        local_definition, remote_definition = _normalize_job_definitions(local_definition, remote_definition)
        return compare_dicts(remote_definition, local_definition)

    def _compare_schedule_definitions(self, local_definition, remote_definition):
        local_definition, remote_definition = _normalize_schedule_definitions(local_definition, remote_definition)
        return compare_dicts(remote_definition, local_definition)


_job_defaults = dict(
    labels=dict(),
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
    parameters=list(),
    privileged=False,

)

_ucr_defaults = dict(
    privileged=False,
    image=dict(forcePull=False, kind="docker")
)


def _normalize_job_definitions(local_definition, remote_definition):
    update_dict_with_defaults(local_definition, _job_defaults)

    local_run = local_definition.get("run", dict())
    update_dict_with_defaults(local_run, _run_defaults)
    if "docker" in local_run:
        update_dict_with_defaults(local_run["docker"], _docker_defaults)
    if "ucr" in local_run:
        update_dict_with_defaults(local_run["ucr"], _ucr_defaults)
    if "gpus" in remote_definition["run"] and "gpus" not in local_run:
        local_run["gpus"] = 0

    return local_definition, remote_definition


def _normalize_schedule_definitions(local_definition, remote_definition):
    if len(remote_definition) > 0:
        remote_definition = remote_definition[0]
    else:
        remote_definition = dict()
    if "nextRunAt" in remote_definition:
        del remote_definition["nextRunAt"]
    if local_definition and "concurrencyPolicy" not in local_definition:
        local_definition["concurrencyPolicy"] = "ALLOW"
    return local_definition, remote_definition


__config__ = MetronomeJob
__manager__ = JobsManager
__config_name__ = "job"
