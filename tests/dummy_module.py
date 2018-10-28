

def parse_config(name, config, variables):
    return Dummy(name, config["test"], config.get("preprocess"))


def preprocess_config(name, config):
    if config.get("pre"):
        config["preprocess"] = True
    return [(name, config)]


class Dummy(object):
    def __init__(self, name, test, preprocess):
        self.name = name
        self.test = test
        self.preprocess = preprocess

    def __eq__(self, value):
        if not isinstance(value, Dummy):
            return False
        return self.name == value.name and self.test == value.test

    def __ne__(self, value):
        return not self.__eq__(value)


class DummiesManager(object):
    pass


__config__ = Dummy
__manager__ = DummiesManager
__config_name__ = "dummy"
