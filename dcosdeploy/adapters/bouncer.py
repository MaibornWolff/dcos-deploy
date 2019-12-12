from ..auth import get_base_url
from ..util import http
from ..util.output import echo_error


class BouncerAdapter(object):
    def __init__(self):
        self.base_url = get_base_url() + "/acs/api/v1"

    def get_account(self, name):
        response = http.get(self.base_url+"/users/"+name)
        if response.status_code != 200:
            return None
        return response.json()

    def create_account(self, name, description, public_key):
        data = dict(description=description, public_key=public_key)
        response = http.put(self.base_url+"/users/"+name, json=data)
        if not response.ok:
            echo_error(response.text)
            raise Exception("Error occured when creating account")

    def delete_account(self, name):
        response = http.delete(self.base_url+"/users/"+name)
        if response.ok:
            return True
        elif response.status_code == 404:
            return False
        else:
            raise Exception("Error occured when deleting account: %s" % response.text)

    def get_groups_for_user(self, name):
        response = http.get(self.base_url+"/users/%s/groups" % name)
        if not response.ok:
            echo_error(response.text)
            raise Exception("Error occured when querying groups for user")
        return [g["group"]["gid"] for g in response.json()["array"]]

    def get_permissions_for_user(self, name):
        response = http.get(self.base_url+"/users/%s/permissions" % name)
        if not response.ok:
            echo_error(response.text)
            raise Exception("Error occured when querying permissions for user")
        permissions = dict()
        for permission in response.json()["direct"]:
            permissions[permission["rid"]] = [a["name"] for a in permission["actions"]]
        return permissions

    def add_user_to_group(self, user_name, group):
        response = http.put(self.base_url+"/groups/%s/users/%s" % (group, user_name))
        if not response.ok:
            echo_error(response.text)
            raise Exception("Error occured when adding user to group")

    def remove_user_from_group(self, user_name, group):
        response = http.delete(self.base_url+"/groups/%s/users/%s" % (group, user_name))
        if not response.ok:
            echo_error(response.text)
            raise Exception("Error occured when adding user to group")

    def add_permission_to_user(self, user_name, rid, action):
        rid = self._encode_rid(rid)
        response = http.put(self.base_url+r"/acls/%s/users/%s/%s" % (rid, user_name, action))
        if not response.ok:
            echo_error(response.text)
            raise Exception("Error occured when adding permission to user")

    def remove_permission_from_user(self, user_name, rid, action):
        rid = self._encode_rid(rid)
        response = http.delete(self.base_url+"/acls/%s/users/%s/%s" % (rid, user_name, action))
        if not response.ok:
            echo_error(response.text)
            raise Exception("Error occured when removing permission from user")

    def create_permission(self, rid):
        rid = self._encode_rid(rid)
        response = http.put(self.base_url+"/acls/%s" % rid, json=dict(description="created by dcos-deploy"))
        if not response.ok:
            echo_error(response.text)
            raise Exception("Error occured when creating permission")

    def get_rids(self):
        response = http.get(self.base_url+"/acls")
        if not response.ok:
            echo_error(response.text)
            raise Exception("Error occured when listing permission")
        return [acl["rid"] for acl in response.json()["array"]]

    def _encode_rid(self, rid):
        return rid.replace("/", r"%252F")
