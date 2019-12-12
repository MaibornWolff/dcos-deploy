"""
The functions in this module work as thin wrappers around their corresponding requests functions. They handle DC/OS adminrouter authentication and ssl verification.
If the URL provided does not start with 'http:' or 'https:' it will be prefixed with the base url of the DC/OS cluster.
"""

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from ..auth import get_base_url, get_auth

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


# Use requests session to allow for connection reuse 
_session = requests.Session()


def get(url, **kwargs):
    return _session.get(_format_url(url), auth=get_auth(), verify=False, **kwargs)


def post(url, **kwargs):
    return _session.post(_format_url(url), auth=get_auth(), verify=False, **kwargs)


def put(url, **kwargs):
    return _session.put(_format_url(url), auth=get_auth(), verify=False, **kwargs)


def patch(url, **kwargs):
    return _session.patch(_format_url(url), auth=get_auth(), verify=False, **kwargs)


def delete(url, **kwargs):
    return _session.delete(_format_url(url), auth=get_auth(), verify=False, **kwargs)


def _format_url(url):
    if not url.startswith("http:") and not url.startswith("https:"):
        if not url.startswith("/"):
            url = "/" + url
        return get_base_url() + url 
    return url
