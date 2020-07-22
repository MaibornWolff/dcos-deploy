import time
from ..auth import get_base_url
from ..base import APIRequestException
from ..util import http
from ..util.output import echo_error


class MarathonAdapter:
    def __init__(self):
        self.marathon_url = get_base_url() + "/service/marathon/v2"

    def get_app_state(self, app_id):
        if not app_id[0] == "/":
            app_id = "/" + app_id
        response = http.get(self.marathon_url+"/apps%s/?embed=app.counts" % app_id)
        if not response.ok:
            if response.status_code == 404:
                return None
            echo_error(response.text)
            raise APIRequestException("Failed to get state for %s" % app_id, response)
        return response.json()["app"]

    def get_deployments(self):
        response = http.get(self.marathon_url+"/deployments")
        if not response.ok:
            echo_error(response.text)
            raise APIRequestException("Failed to get deployments", response)
        return response.json()

    def get_deployment(self, deployment_id):
        deployments = self.get_deployments()
        for deployment in deployments:
            if deployment["id"] == deployment_id:
                return deployment
        return None

    def wait_for_specific_deployment(self, deployment_id):
        wait_time = 0
        deployment = self.get_deployment(deployment_id)
        while deployment:
            if wait_time > 10*60:
                raise Exception("Deployment did not complete after 10 minutes")
            time.sleep(10)
            wait_time += 10
            deployment = self.get_deployment(deployment_id)

    def wait_for_deployment(self, app_id):
        wait_time = 0
        state = self.get_app_state(app_id)
        while state and len(state["deployments"]) != 0:
            if wait_time > 10*60:
                raise Exception("Deployment for %s did not complete after 10 minutes" % app_id)
            time.sleep(10)
            wait_time += 10
            state = self.get_app_state(app_id)
    
    def wait_for_deletion(self, app_id):
        wait_time = 0
        state = self.get_app_state(app_id)
        while state:
            if wait_time > 10*60:
                raise Exception("Deployment for %s did not complete after 10 minutes" % app_id)
            time.sleep(10)
            wait_time += 10
            state = self.get_app_state(app_id)

    def deploy_app(self, app_definition, wait_for_deployment=False, force=False):
        response = http.put(self.marathon_url + "/apps?force=%s" % force, json=[app_definition])
        if not response.ok:
            echo_error(response.text)
            raise APIRequestException("Failed to deploy app %s" % app_definition["id"], response)
        deployment_id = response.json()["deploymentId"]
        deployment = self.get_deployment(deployment_id)
        if not deployment:
            return False
        if wait_for_deployment:
            self.wait_for_specific_deployment(deployment_id)
        return True

    def restart_app(self, app_id, wait_for_deployment=False, force=False):
        response = http.post(self.marathon_url + "/apps/%s/restart?force=%s" % (app_id, force))
        if not response.ok:
            echo_error(response.text)
            raise APIRequestException("Failed to restart app %s" % app_id, response)
        deployment_id = response.json()["deploymentId"]
        if wait_for_deployment:
            self.wait_for_specific_deployment(deployment_id)

    def delete_app(self, app_id, wait_for_deployment=False, force=False):
        response = http.delete(self.marathon_url + "/apps/%s?force=%s" % (app_id, force))
        if not response.ok:
            if response.status_code == 404:
                return False
            echo_error(response.text)
            raise APIRequestException("Failed to delete app %s" % app_id, response)
        deployment_id = response.json()["deploymentId"]
        if wait_for_deployment:
            self.wait_for_specific_deployment(deployment_id)
        return True

    def get_group(self, name):
        response = http.get(self.marathon_url+"/groups/%s" % name)
        if not response.ok:
            if response.status_code == 404:
                return None
            echo_error(response.text)
            raise APIRequestException("Failed to get marathon group %s" % name, response)
        return response.json()

    def update_group(self, name, enforce_role):
        response = http.put(self.marathon_url+"/groups/%s" % name, json={'enforceRole': enforce_role})
        if not response.ok:
            raise APIRequestException("Error while updating marathon group %s" % name, response)
        return response.json()

    def add_group(self, name, enforce_role=False):
        response = http.post(self.marathon_url+"/groups/", json={'id': name, 'enforceRole': enforce_role})
        if not response.ok:
            raise APIRequestException("Error while creating marathon group %s" % name, response)
        return response.json()

    def delete_group(self, name):
        response = http.delete(self.marathon_url+"/groups/%s" % name)
        if not response.ok:
            raise APIRequestException("Error while removing marathon group %s" % name, response)
        return response.json()
