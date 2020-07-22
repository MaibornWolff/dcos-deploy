

class ConfigurationException(Exception):
    pass


class APIRequestException(Exception):
    """An adapter encountered an error while calling a remote API. The response field contains the Response object from the requests library"""
    def __init__(self, expression, response):
        super().__init__(expression)
        self.response = response