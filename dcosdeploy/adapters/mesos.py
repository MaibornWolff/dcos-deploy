import uuid
import base64
import json
from ..auth import get_base_url
from ..base import APIRequestException
from ..util import http
from ..util.output import echo_error


class MesosAdapter:
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
        response = http.post(url, json=action)
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
            echo_error(response.text)
            raise APIRequestException("Unknown error occured", response)

    def get_container_id_and_slave_id_for_task(self, name):
        state = self._get_master_state()
        parent_container_id, slave_id = _find_task(state["frameworks"], name, exact_match=True)
        if not parent_container_id:
            parent_container_id, slave_id = _find_task(state["frameworks"], name, exact_match=False)
        return parent_container_id, slave_id

    def _get_master_state(self):
        response = http.get(self.mesos_url+"master/state")
        if response.ok:
            return response.json()
        else:
            raise APIRequestException("Failed to get mesos master state", response)

    def update_quota(self, name, quota, force=True):
        request_body = {
            "type": "UPDATE_QUOTA",
            "update_quota": {
                "force": force,
                "quota_configs": [{
                    "role": name,
                    "limits": {
                        "cpus": {
                            "value": quota.cpus
                        },
                        "mem": {
                            "value": quota.mem
                        },
                        "disk": {
                            "value": quota.disk
                        },
                        "gpus": {
                            "value": quota.gpus
                        }
                    }
                }
                ]
            }
        }
        response = http.post(self.mesos_url+"/api/v1", json=request_body)
        if not response.ok:
            raise APIRequestException("Error while updating quota", response)
        return response.status_code

    def get_quota(self, name):
        roles = http.get(self.mesos_url+"roles").json()["roles"]
        try:
            return [x for x in roles if x['name'] == name][0]["quota"]
        except:
            return None


def _find_task(frameworks, name, exact_match=False):
    parent_container_id = None
    slave_id = None
    for framework in frameworks:
        for task in framework["tasks"]:
            # split(".") is done to only get the name part of marathon tasks
            if task["state"] == "TASK_RUNNING" and (name == task["id"].split(".")[0] if exact_match else name in task["id"]):
                if parent_container_id:
                    raise Exception("Task identifier '%s' is not unique" % name)
                slave_id = task["slave_id"]
                for state in task["statuses"]:
                    if state["state"] == "TASK_RUNNING":
                        parent_container_id = state["container_status"]["container_id"]
                        break
    return parent_container_id, slave_id