import requests
from ..base import ConfigurationException
from ..util.output import echo 
from ..auth import get_base_url, get_auth


class HttpCall(object):
    def __init__(self, url, method, content, use_adminrouter, ignore_errors):
        self.url = url
        self.method = method
        self.content = content
        self.use_adminrouter = use_adminrouter
        self.ignore_errors = ignore_errors


def parse_config(name, config, config_helper):
    url = config.get("url")
    method = config.get("method", "GET")
    body = config.get("body", dict())
    ignore_errors = config.get("ignore_errors", False)
    if not url:
        raise ConfigurationException("url is required for httpcall '%s'" % name)

    url = config_helper.render(url)
    use_adminrouter = not url.startswith("http:") and not url.startswith("https:")
    if use_adminrouter:
        if url[0] == "/":
            url = url[1:]
        url = get_base_url()+"/"+url

    content = None
    if "file" in body:
        filename = config_helper.render(body["file"])
        content = config_helper.read_file(filename, render_variables=body.get("render", False))
    elif "content" in body:
        content = body["content"]
        if body.get("render", False):
            content = config_helper.render(content)

    return HttpCall(url, method, content, use_adminrouter, ignore_errors)


class HttpCallManager(object):
    def __init__(self):
        pass

    def deploy(self, config, dependencies_changed=False, force=False):
        echo("\tDoing HTTP call")
        auth = get_auth() if config.use_adminrouter else None
        response = requests.request(config.method, config.url, auth=auth, data=config.content, verify=False)
        if not response.ok and not config.ignore_errors:
            raise Exception("Got response {}: {}".format(response.status_code, response.text))
        echo("\tGot response {}.".format(response.status_code))
        return True

    def dry_run(self, config, dependencies_changed=False):
        echo("Would do HTTP %s call to '%s'" % (config.method, config.url))
        return True

    def delete(self, config, force=False):
        return False

    def dry_delete(self, config):
        return False


__config__ = HttpCall
__manager__ = HttpCallManager
__config_name__ = "httpcall"
