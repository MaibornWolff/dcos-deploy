import time
from ..auth import get_base_url
from ..base import APIRequestException
from ..util import http
from ..util.output import echo_error


class MetronomeAdapter:
    def __init__(self):
        self.metronome_url = get_base_url() + "/service/metronome/"

    def create_job(self, definition):
        response = http.post(self.metronome_url+"v1/jobs", json=definition)
        if response.ok:
            return
        if response.status_code == 422:
            echo_error(response.text)
            raise APIRequestException("Invalid job definition", response)
        else:
            echo_error(response.text)
            raise APIRequestException("Unknown error occured", response)

    def update_job(self, job_id, definition):
        response = http.put(self.metronome_url+"v1/jobs/%s" % job_id, json=definition)
        if response.ok:
            return
        if response.status_code == 422:
            echo_error(response.text)
            raise APIRequestException("Invalid job definition", response)
        elif response.status_code == 404:
            raise APIRequestException("Job does not exist", response)
        else:
            echo_error(response.text)
            raise APIRequestException("Unknown error occured", response)

    def get_jobs(self):
        response = http.get(self.metronome_url+"v1/jobs")
        if not response.ok:
            echo_error(response.text)
            raise APIRequestException("Unknown error occured", response)
        data = response.json()
        for job in data:
            yield job["id"]

    def get_job(self, job_id, embed_history=False):
        if job_id[0] == "/":
            job_id = job_id[1:]
        params = ""
        if embed_history:
            params = "?embed=history"
        response = http.get(self.metronome_url+"v1/jobs/%s%s" % (job_id, params))
        if response.ok:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            echo_error(response.text)
            raise APIRequestException("Unknown error occured", response)

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
            raise APIRequestException("Unknown error occured", response)

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
            raise APIRequestException("Unknown error occured", response)

    def create_schedule(self, job_id, definition):
        response = http.post(self.metronome_url+"v1/jobs/%s/schedules" % job_id, json=definition)
        if response.ok:
            return
        if response.status_code == 422:
            echo_error(response.text)
            raise APIRequestException("Invalid job definition", response)
        else:
            echo_error(response.text)
            raise APIRequestException("Unknown error occured", response)

    def update_schedule(self, job_id, definition):
        response = http.put(self.metronome_url+"v1/jobs/%s/schedules/%s" % (job_id, definition["id"]), json=definition)
        if response.ok:
            return
        if response.status_code == 422:
            echo_error(response.text)
            raise APIRequestException("Invalid job definition", response)
        else:
            echo_error(response.text)
            raise APIRequestException("Unknown error occured", response)

    def delete_schedule(self, job_id, schedule_id):
        response = http.delete(self.metronome_url+"v1/jobs/%s/schedules/%s" % (job_id, schedule_id))
        if response.ok:
            return True
        elif response.status_code == 404:
            return False
        else:
            echo_error(response.text)
            raise APIRequestException("Unknown error occured", response)

    def trigger_job_run(self, job_id):
        response = http.post(self.metronome_url+"v1/jobs/%s/runs" % job_id)
        if response.ok:
            return response.json()["id"]
        else:
            echo_error(response.text)
            raise APIRequestException("Failed to start job", response)

    def get_job_run_status(self, job_id, run_id):
        response = http.get(self.metronome_url+"v1/jobs/%s/runs/%s" % (job_id, run_id))
        if response.ok:
            return response.json()["status"]
        elif response.status_code == 404:
            return None
        else:
            echo_error(response.text)
            raise APIRequestException("Failed to get job status", response)

    def wait_for_job_run(self, job_id, run_id, timeout=10*60):
        wait_time = 0
        status = self.get_job_run_status(job_id, run_id)
        while status and status not in ("SUCCESS", "FAILED"):
            if wait_time > timeout:
                raise Exception("Job %s run %s did not finish after %s seconds" % (job_id, run_id, timeout))
            time.sleep(10)
            wait_time += 10
            status = status = self.get_job_run_status(job_id, run_id)
        job = self.get_job(job_id, embed_history=True)
        history = job.get("history", dict())
        for run in history.get("successfulFinishedRuns", list()):
            if run["id"] == run_id:
                return True
        raise Exception("Job %s run %s failed" % (job_id, run_id))
