import time
import requests
from dcosdeploy.auth import get_auth, get_base_url

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class MarathonAdapter(object):
    def __init__(self):
        self.marathon_url = get_base_url() + "/service/marathon/v2"

    def get_app_state(self, app_id):
        if not app_id[0] == "/":
            app_id = "/" + app_id
        response = requests.get(self.marathon_url+"/apps%s/?embed=app.counts" % app_id, auth=get_auth(), verify=False)
        if not response.ok:
            if response.status_code == 404:
                return None
            print(response.text, flush=True)
            raise Exception("Failed to get state for %s" % app_id)
        return response.json()["app"]

    def get_deployments(self):
        response = requests.get(self.marathon_url+"/deployments", auth=get_auth(), verify=False)
        if not response.ok:
            print(response.text, flush=True)
            raise Exception("Failed to get deployments")
        return response.json()

    def get_deployment(self, deployment_id):
        deployments = self.get_deployments()
        for deployment in deployments:
            if deployment["id"] == deployment_id:
                return deployment
        return None

    def wait_for_deployment(self, app_id):
        wait_time = 0
        state = self.get_app_state(app_id)
        while len(state["deployments"]) != 0:
            if wait_time > 10*60:
                raise Exception("Deployment for %s did not complete after 10 minutes" % app_id)
            time.sleep(10)
            wait_time += 10
            state = self.get_app_state(app_id)

    def deploy_app(self, app_definition, wait_for_deployment=False):
        response = requests.put(self.marathon_url + "/apps", json=[app_definition], auth=get_auth(), verify=False)
        if not response.ok:
            print(response.text, flush=True)
            raise Exception("Failed to deploy app %s" % app_definition["id"])
        deployment_id = response.json()["deploymentId"]
        deployment = self.get_deployment(deployment_id)
        if not deployment:
            return False
        if wait_for_deployment:
            self.wait_for_deployment(app_definition["id"])
        return True

    def restart_app(self, app_id, wait_for_deployment=False):
        response = requests.post(self.marathon_url + "/apps/%s/restart" % app_id, auth=get_auth(), verify=False)
        if not response.ok:
            print(response.text, flush=True)
            raise Exception("Failed to restart app %s" % app_id)
        if wait_for_deployment:
            self.wait_for_deployment(app_id)
