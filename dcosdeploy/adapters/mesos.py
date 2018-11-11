import uuid
import base64
import json
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from dcosdeploy.auth import get_base_url, get_auth

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class MesosAdapter(object):
    def __init__(self):
        self.base_url = get_base_url()
        self.mesos_url = self.base_url + "/mesos/"

    def launch_nested_container(self, slave_id, parent_container_id, command, shell=False):
        url = "%s/slave/%s/api/v1" % (self.base_url, slave_id)
        new_container_id = str(uuid.uuid4())
        action = {
          "type": "LAUNCH_NESTED_CONTAINER_SESSION",
          "launch_nested_container_session": {
            "command": {
              "shell": shell,
              "arguments": command,
              "value": command[0]
            },
            "container_id": {
              "parent": parent_container_id,
              "value": new_container_id
            }
          }
        }
        response = requests.post(url, json=action, auth=get_auth(), verify=False)
        if response.ok:
            lines = response.text.split("\n")
            idx = 1
            result_text = ""
            line = lines[0]
            while idx < len(lines):
                content_len = int(line)
                data = json.loads(lines[idx][:content_len])
                line = lines[idx][content_len:]
                text = base64.b64decode(data.get("data", dict()).get("data", "")).decode("utf-8")
                result_text += text
                idx += 1
            return result_text
        else:
            raise Exception("Unknown error occured: %s" % response.text)

    def get_container_id_and_slave_id_for_task(self, name):
        state = self._get_master_state()
        parent_container_id = None
        slave_id = None
        for framework in state["frameworks"]:
            for task in framework["tasks"]:
                if task["state"] == "TASK_RUNNING" and name in task["id"]:
                    if parent_container_id:
                        raise Exception("Task identifier '%s' is not unique" % (name))
                    slave_id = task["slave_id"]
                    for state in task["statuses"]:
                        if state["state"] == "TASK_RUNNING":
                            parent_container_id = state["container_status"]["container_id"]
                            break
        return parent_container_id, slave_id

    def _get_master_state(self):
        response = requests.get(self.mesos_url+"master/state", auth=get_auth(), verify=False)
        if response.ok:
            return response.json()
        else:
            raise Exception("Failed to get mesos master state: %s" % response.text)
