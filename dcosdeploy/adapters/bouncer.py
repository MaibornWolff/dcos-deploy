from ..auth import get_base_url
from ..base import APIRequestException
from ..util import http
from ..util.output import echo_error


class BouncerAdapter:
    def __init__(self):
        self.base_url = get_base_url() + "/acs/api/v1"

    def get_account(self, name):
        response = http.get(self.base_url+"/users/"+name)
        if response.status_code != 200:
            return None
        return response.json()

    def create_service_account(self, name, description, public_key):
        data = dict(description=description, public_key=public_key)
        response = http.put(self.base_url+"/users/"+name, json=data)
        if not response.ok:
            echo_error(response.text)
            raise APIRequestException("Error occured when creating account", response)

    def create_user(self, name, password, full_name, provider_type=None, provider_id=None):
        data = dict(description=full_name, password=password)
        if provider_type:
            data["provider_type"] = provider_type
        if provider_id:
            data["provider_id"] = provider_id
        response = http.put(self.base_url+"/users/"+name, json=data)
        if not response.ok:
            echo_error(response.text)
            raise APIRequestException("Error occured when creating user", response)

    def update_user(self, name, password=None, full_name=None):
        data = dict()
        if password:
            data["password"] = password
        if full_name:
            data["description"] = full_name
        response = http.patch(self.base_url+"/users/"+name, json=data)
        if not response.ok:
            echo_error(response.text)
            raise APIRequestException("Error occured when updating user", response)

    def delete_account(self, name):
        response = http.delete(self.base_url+"/users/"+name)
        if response.ok:
            return True
        elif response.status_code == 404:
            return False
        else:
            echo_error(response.text)
            raise APIRequestException("Error occured when deleting account", response)

    def get_groups_for_user(self, name):
        response = http.get(self.base_url+"/users/%s/groups" % name)
        if not response.ok:
            echo_error(response.text)
            raise APIRequestException("Error occured when querying groups for user", response)
        return [g["group"]["gid"] for g in response.json()["array"]]

    def get_permissions_for_user(self, name):
        response = http.get(self.base_url+"/users/%s/permissions" % name)
        if not response.ok:
            echo_error(response.text)
            raise APIRequestException("Error occured when querying permissions for user", response)
        permissions = dict()
        for permission in response.json()["direct"]:
            permissions[permission["rid"]] = [a["name"] for a in permission["actions"]]
        return permissions

    def add_user_to_group(self, user_name, group):
        response = http.put(self.base_url+"/groups/%s/users/%s" % (group, user_name))
        if not response.ok:
            echo_error(response.text)
            raise APIRequestException("Error occured when adding user to group", response)

    def remove_user_from_group(self, user_name, group):
        response = http.delete(self.base_url+"/groups/%s/users/%s" % (group, user_name))
        if not response.ok:
            echo_error(response.text)
            raise APIRequestException("Error occured when adding user to group", response)

    def add_permission_to_user(self, user_name, rid, action):
        rid = self._encode_rid(rid)
        response = http.put(self.base_url+r"/acls/%s/users/%s/%s" % (rid, user_name, action))
        if not response.ok:
            echo_error(response.text)
            raise APIRequestException("Error occured when adding permission to user", response)

    def remove_permission_from_user(self, user_name, rid, action):
        rid = self._encode_rid(rid)
        response = http.delete(self.base_url+"/acls/%s/users/%s/%s" % (rid, user_name, action))
        if not response.ok:
            echo_error(response.text)
            raise APIRequestException("Error occured when removing permission from user", response)

    def create_permission(self, rid):
        rid = self._encode_rid(rid)
        response = http.put(self.base_url+"/acls/%s" % rid, json=dict(description="created by dcos-deploy"))
        if not response.ok:
            echo_error(response.text)
            raise APIRequestException("Error occured when creating permission", response)

    def get_rids(self):
        response = http.get(self.base_url+"/acls")
        if not response.ok:
            echo_error(response.text)
            raise APIRequestException("Error occured when listing permission", response)
        return [acl["rid"] for acl in response.json()["array"]]

    def create_group(self, name, description, provider_type):
        data = dict(description=description)
        if provider_type:
            data["provider_type"] = provider_type
        response = http.put(self.base_url+"/groups/"+name, json=data)
        if not response.ok:
            echo_error(response.text)
            raise APIRequestException("Error occured when creating group", response)

    def update_group(self, name, description):
        data = dict(description=description)
        response = http.patch(self.base_url+"/groups/"+name, json=data)
        if not response.ok:
            echo_error(response.text)
            raise APIRequestException("Error occured when updating group", response)

    def delete_group(self, name):
        response = http.delete(self.base_url+"/groups/"+name)
        if response.ok:
            return True
        elif response.status_code == 404:
            return False
        else:
            echo_error(response.text)
            raise APIRequestException("Error occured when deleting group", response)

    def get_group(self, name):
        response = http.get(self.base_url+"/groups/"+name)
        if response.status_code != 200:
            return None
        return response.json()

    def get_permissions_for_group(self, name):
        response = http.get(self.base_url+"/groups/%s/permissions" % name)
        if not response.ok:
            echo_error(response.text)
            raise APIRequestException("Error occured when querying permissions for group", response)
        permissions = dict()
        for permission in response.json()["array"]:
            permissions[permission["rid"]] = [a["name"] for a in permission["actions"]]
        return permissions

    def add_permission_to_group(self, group_name, rid, action):
        rid = self._encode_rid(rid)
        response = http.put(self.base_url+r"/acls/%s/groups/%s/%s" % (rid, group_name, action))
        if not response.ok:
            echo_error(response.text)
            raise APIRequestException("Error occured when adding permission to group", response)

    def remove_permission_from_group(self, group_name, rid, action):
        rid = self._encode_rid(rid)
        response = http.delete(self.base_url+"/acls/%s/groups/%s/%s" % (rid, group_name, action))
        if not response.ok:
            echo_error(response.text)
            raise APIRequestException("Error occured when removing permission from group", response)

    def _encode_rid(self, rid):
        return rid.replace("/", r"%252F")
