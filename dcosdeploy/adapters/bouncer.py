import requests
from dcosdeploy.auth import get_base_url, get_auth


class BouncerAdapter(object):
    def __init__(self):
        self.base_url = get_base_url() + "/acs/api/v1"

    def get_account(self, name):
        response = requests.get(self.base_url+"/users/"+name, auth=get_auth(), verify=False)
        if response.status_code != 200:
            return None
        return response.json()

    def create_account(self, name, description, public_key):
        data = dict(description=description, public_key=public_key)
        response = requests.put(self.base_url+"/users/"+name, json=data, auth=get_auth(), verify=False)
        if not response.ok:
            print(response.text)
            raise Exception("Error occured when creating account")

    def get_groups_for_user(self, name):
        response = requests.get(self.base_url+"/users/%s/groups" % name, auth=get_auth(), verify=False)
        if not response.ok:
            print(response.text)
            raise Exception("Error occured when querying groups for user")
        return [g["group"]["gid"] for g in response.json()["array"]]

    def get_permissions_for_user(self, name):
        response = requests.get(self.base_url+"/users/%s/permissions" % name, auth=get_auth(), verify=False)
        if not response.ok:
            print(response.text)
            raise Exception("Error occured when querying permissions for user")
        permissions = dict()
        for permission in response.json()["direct"]:
            permissions[permission["rid"]] = [a["name"] for a in permission["actions"]]
        return permissions

    def add_user_to_group(self, user_name, group):
        response = requests.put(self.base_url+"/groups/%s/users/%s" % (group, user_name), auth=get_auth(), verify=False)
        if not response.ok:
            print(response.text)
            raise Exception("Error occured when adding user to group")

    def remove_user_from_group(self, user_name, group):
        response = requests.delete(self.base_url+"/groups/%s/users/%s" % (group, user_name), auth=get_auth(), verify=False)
        if not response.ok:
            print(response.text)
            raise Exception("Error occured when adding user to group")

    def add_permission_to_user(self, user_name, rid, action):
        rid = rid.replace("/", r"%252F")
        response = requests.put(self.base_url+r"/acls/%s/users/%s/%s" % (rid, user_name, action), auth=get_auth(), verify=False)
        if not response.ok:
            print(response.text)
            raise Exception("Error occured when adding permission to user")

    def remove_permission_from_user(self, user_name, rid, action):
        rid = rid.replace("/", r"%252F")
        response = requests.delete(self.base_url+"/acls/%s/users/%s/%s" % (rid, user_name, action), auth=get_auth(), verify=False)
        if not response.ok:
            print(response.text)
            raise Exception("Error occured when removing permission from user")
