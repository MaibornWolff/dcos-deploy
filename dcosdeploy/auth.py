import json
import os
import re
import subprocess
import time
import jwt
import requests
from requests.auth import AuthBase


ENV_BASE_URL = "DCOS_BASE_URL"
ENV_AUTH_TOKEN = "DCOS_AUTH_TOKEN"
ENV_USERNAME = "DCOS_USERNAME"
ENV_PASSWORD = "DCOS_PASSWORD"
ENV_DCOS_SERVICE_ACCOUNT_CREDENTIAL = "DCOS_SERVICE_ACCOUNT_CREDENTIAL"
LOGIN_ENDPOINT = "/acs/api/v1/auth/login"


_base_url = None
_auth = None


class StaticTokenAuth(AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, auth_request):
        auth_request.headers['Authorization'] = 'token=' + self.token
        return auth_request


def _read_config_from_dcos_cli():
    global _base_url, _auth
    try:
        _base_url = _get_property_from_cli("core.dcos_url")
        _auth = StaticTokenAuth(_get_property_from_cli("core.dcos_acs_token"))
        return True
    except:
        return False


def _get_property_from_cli(property_name):
    res = subprocess.run(["dcos", "config", "show", property_name], shell=False, stdout=subprocess.PIPE)
    return res.stdout.strip().decode("utf-8")


def _read_config_from_toml():
    global _base_url, _auth
    filename = _determine_dcos_cluster_config_file()
    if not filename:
        return False
    with open(filename) as config_file:
        data = config_file.read()
    matches = re.findall(r"dcos_acs_token = \"(\S+)\"", data)
    if matches:
        _auth = StaticTokenAuth(matches[0])
    matches = re.findall(r"dcos_url = \"(\S+)\"", data)
    if matches:
        _base_url = matches[0]
        return True
    else:
        return False


def _determine_dcos_cluster_config_file():
    home = os.path.expanduser("~")
    clusters_path = os.path.join(home, ".dcos", "clusters")
    if os.path.exists(clusters_path):
        for cluster_id in os.listdir(clusters_path):
            if os.path.exists(os.path.join(clusters_path, cluster_id, "attached")):
                return os.path.join(clusters_path, cluster_id, "dcos.toml")
    return None


def _read_config_from_env():
    global _base_url, _auth
    if ENV_BASE_URL in os.environ and ENV_AUTH_TOKEN in os.environ:
        _base_url = os.environ.get(ENV_BASE_URL)
        _auth = StaticTokenAuth(os.environ.get(ENV_AUTH_TOKEN))
        return True
    elif ENV_BASE_URL in os.environ and ENV_USERNAME in os.environ and ENV_PASSWORD in os.environ:
        _base_url = os.environ.get(ENV_BASE_URL)
        username = os.environ.get(ENV_USERNAME)
        password = os.environ.get(ENV_PASSWORD)
        login_endpoint = _base_url + LOGIN_ENDPOINT
        now = int(time.time())
        data = {
            'uid': username,
            'password': password,
            'exp': now + 30*60, # expiry time for the token
        }
        r = requests.post(login_endpoint, json=data, timeout=(3.05, 46), verify=False)
        r.raise_for_status()
        _auth = StaticTokenAuth(r.cookies['dcos-acs-auth-cookie'])
        return True
    else:
        return False


def _read_config_from_service_account():
    global _base_url, _auth
    credentials = os.environ.get(ENV_DCOS_SERVICE_ACCOUNT_CREDENTIAL)
    if not credentials:
        return False
    credentials = json.loads(credentials)
    _base_url = os.environ.get(ENV_BASE_URL)
    if not credentials or not _base_url:
        return False
    uid = credentials["uid"]
    private_key = credentials["private_key"]
    login_endpoint = credentials['login_endpoint']
    now = int(time.time())
    payload = {
        'uid': uid,
        'exp': now + 60, # expiry time of the auth request params
    }
    token = jwt.encode(payload, private_key, 'RS256')

    data = {
        'uid': uid,
        'token': token.decode('ascii'),
        'exp': now + 30*60, # expiry time for the token
    }
    r = requests.post(login_endpoint, json=data, timeout=(3.05, 46), verify=False)
    r.raise_for_status()
    _auth = StaticTokenAuth(r.cookies['dcos-acs-auth-cookie'])
    return True


def _init_config():
    global _base_url, _auth 
    for func in [_read_config_from_env, _read_config_from_service_account, _read_config_from_toml, _read_config_from_dcos_cli]:
        func()
        if _base_url and _auth:
            # Remove slash from end of URL as adapters assume no slash
            if _base_url[-1] == "/":
                _base_url = _base_url[:-1]
            return
    raise Exception("Could not find working authentication method for DC/OS cluster")


def get_base_url():
    global _base_url
    if not _base_url:
        _init_config()
    return _base_url


def get_auth():
    global _auth
    if not _auth:
        _init_config()
    return _auth

