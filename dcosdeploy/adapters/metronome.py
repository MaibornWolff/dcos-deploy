import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from dcosdeploy.auth import get_base_url, get_auth

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class MetronomeAdapter(object):
    def __init__(self):
        self.metronome_url = get_base_url() + "/service/metronome/"

    def create_job(self, definition):
        response = requests.post(self.metronome_url+"v0/scheduled-jobs", json=definition, auth=get_auth(), verify=False)
        if response.ok:
            return
        if response.status_code == 422:
            print(response.text)
            raise Exception("Invalid job definition")
        else:
            print(response.text)
            raise Exception("Unknown error occured")

    def update_job(self, definition):
        response = requests.put(self.metronome_url+"v0/scheduled-jobs/%s" % definition["id"], json=definition, auth=get_auth(), verify=False)
        if response.ok:
            return
        if response.status_code == 422:
            print(response.text)
            raise Exception("Invalid job definition")
        elif response.status_code == 404:
            raise Exception("Job does not exist")
        else:
            print(response.text)
            raise Exception("Unknown error occured")

    def get_jobs(self):
        response = requests.get(self.metronome_url+"v1/jobs", auth=get_auth(), verify=False)
        if not response.ok:
            print(response.text)
            raise Exception("Unknown error occured")
        data = response.json()
        for job in data:
            yield "/"+job["id"].replace(".", "/")

    def get_job(self, job_id):
        if job_id[0] == "/":
            job_id = job_id[1:]
        job_id = job_id.replace("/", ".")
        response = requests.get(self.metronome_url+"v1/jobs/%s?embed=schedules" % job_id, auth=get_auth(), verify=False)
        if response.ok:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            print(response.text)
            raise Exception("Unknown error occured")

    def does_job_exist(self, job_id):
        return job_id in list(self.get_jobs())
