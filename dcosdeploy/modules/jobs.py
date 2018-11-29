from dcosdeploy.base import ConfigurationException
from dcosdeploy.adapters.metronome import MetronomeAdapter
from dcosdeploy.util import compare_dicts, print_if


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
    job_definition = config_helper.read_json(job_definition_path, render_variables=True)
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
            existing_job_definition = self.api.get_job(config.job_id)
            if not self.compare_job_definitions(existing_job_definition, config.job_definition):
                print_if(not silent, "\tUpdating existing job")
                self.api.update_job(config.job_definition)
                print_if(not silent, "\tUpdated job.")
                return True
            print_if(not silent, "\tJob already exists. No update needed.")
            return False
        else:
            print_if(not silent, "\tCreating job")
            self.api.create_job(config.job_definition)
            print_if(not silent, "\tCreated job.")
            return True

    def dry_run(self, config, dependencies_changed=False, print_changes=True, debug=False):
        if not self.api.does_job_exist(config.job_id):
            print("Would create job %s" % config.job_id)
            return True
        existing_job_definition = self.api.get_job(config.job_id)
        changed = not self.compare_job_definitions(existing_job_definition, config.job_definition, debug)
        if changed:
            print("Would update job %s" % config.job_id)
        return changed

    def compare_job_definitions(self, old_job_definition, new_job_definition, debug=False):
        if "schedules" in old_job_definition:
            for schedule in old_job_definition["schedules"]:
                if "nextRunAt" in schedule:
                    del schedule["nextRunAt"]
        return compare_dicts(old_job_definition, new_job_definition, print_differences=debug)


__config__ = MetronomeJob
__manager__ = JobsManager
__config_name__ = "job"
