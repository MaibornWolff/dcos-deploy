from ..auth import get_base_url, get_auth
from ..util import http
from ..util.output import echo_error


class MetronomeAdapter(object):
    def __init__(self):
        self.metronome_url = get_base_url() + "/service/metronome/"

    def create_job(self, definition):
        response = http.post(self.metronome_url+"v1/jobs", json=definition)
        if response.ok:
            return
        if response.status_code == 422:
            echo_error(response.text)
            raise Exception("Invalid job definition")
        else:
            echo_error(response.text)
            raise Exception("Unknown error occured")

    def update_job(self, job_id, definition):
        response = http.put(self.metronome_url+"v1/jobs/%s" % job_id, json=definition)
        if response.ok:
            return
        if response.status_code == 422:
            echo_error(response.text)
            raise Exception("Invalid job definition")
        elif response.status_code == 404:
            raise Exception("Job does not exist")
        else:
            echo_error(response.text)
            raise Exception("Unknown error occured")

    def get_jobs(self):
        response = http.get(self.metronome_url+"v1/jobs")
        if not response.ok:
            echo_error(response.text)
            raise Exception("Unknown error occured")
        data = response.json()
        for job in data:
            yield job["id"]

    def get_job(self, job_id):
        if job_id[0] == "/":
            job_id = job_id[1:]
        response = http.get(self.metronome_url+"v1/jobs/%s" % job_id)
        if response.ok:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            echo_error(response.text)
            raise Exception("Unknown error occured")

    def get_schedules(self, job_id):
        if job_id[0] == "/":
            job_id = job_id[1:]
        response = http.get(self.metronome_url+"v1/jobs/%s/schedules" % job_id)
        if response.ok:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            echo_error(response.text)
            raise Exception("Unknown error occured")

    def does_job_exist(self, job_id):
        return job_id in list(self.get_jobs())

    def delete_job(self, job_id):
        if job_id[0] == "/":
            job_id = job_id[1:]
        response = http.delete(self.metronome_url+"v1/jobs/%s" % job_id)
        if response.ok:
            return True
        elif response.status_code == 404:
            return False
        else:
            echo_error(response.text)
            raise Exception("Unknown error occured")

    def create_schedule(self, job_id, definition):
        response = http.post(self.metronome_url+"v1/jobs/%s/schedules" % job_id, json=definition)
        if response.ok:
            return
        if response.status_code == 422:
            echo_error(response.text)
            raise Exception("Invalid job definition")
        else:
            echo_error(response.text)
            raise Exception("Unknown error occured")

    def update_schedule(self, job_id, definition):
        response = http.put(self.metronome_url+"v1/jobs/%s/schedules/%s" % (job_id, definition["id"]), json=definition)
        if response.ok:
            return
        if response.status_code == 422:
            echo_error(response.text)
            raise Exception("Invalid job definition")
        else:
            echo_error(response.text)
            raise Exception("Unknown error occured")

    def delete_schedule(self, job_id, schedule_id):
        response = http.delete(self.metronome_url+"v1/jobs/%s/schedules/%s" % (job_id, schedule_id))
        if response.ok:
            return True
        elif response.status_code == 404:
            return False
        else:
            echo_error(response.text)
            raise Exception("Unknown error occured")