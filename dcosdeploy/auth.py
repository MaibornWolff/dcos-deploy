import os
import re
import subprocess
from requests.auth import AuthBase


def _get_dcos_url_from_cli():
    res = subprocess.run(["dcos", "config", "show", "core.dcos_url"], shell=False, stdout=subprocess.PIPE)
    return res.stdout.strip().decode("utf-8")


def _get_dcos_token_from_cli():
    res = subprocess.run(["dcos", "config", "show", "core.dcos_acs_token"], shell=False, stdout=subprocess.PIPE)
    return res.stdout.strip().decode("utf-8")


def _determine_dcos_cluster_config_file():
    home = os.path.expanduser("~")
    clusters_path = os.path.join(home, ".dcos", "clusters")
    if os.path.exists(clusters_path):
        for cluster_id in os.listdir(clusters_path):
            if os.path.exists(os.path.join(clusters_path, cluster_id, "attached")):
                return os.path.join(clusters_path, cluster_id, "dcos.toml")
    return None


def _read_config_from_toml():
    filename = _determine_dcos_cluster_config_file()
    if not filename:
        return
    global _base_url, _auth
    with open(filename) as config_file:
        data = config_file.read()
    matches = re.findall(r"dcos_acs_token = \"(\S+)\"", data)
    if matches:
        _auth = StaticTokenAuth(matches[0])
    matches = re.findall(r"dcos_url = \"(\S+)\"", data)
    if matches:
        _base_url = matches[0]
        # Remove slash from end of URL as adapters assume no slash
        if _base_url[-1] == "/":
            _base_url = _base_url[:-1]


class StaticTokenAuth(AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, auth_request):
        auth_request.headers['Authorization'] = 'token=' + self.token
        return auth_request


_base_url = None
_auth = None


def get_base_url():
    global _base_url
    if not _base_url:
        _read_config_from_toml()
        if not _base_url:
            _base_url = _get_dcos_url_from_cli()
    return _base_url


def get_auth():
    global _auth
    if not _auth:
        _read_config_from_toml()
        if not _auth:
            _auth = StaticTokenAuth(_get_dcos_token_from_cli())
    return _auth
