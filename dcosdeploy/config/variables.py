import os
import base64
import pystache
from ..base import ConfigurationException
from ..util import decrypt_data
from ..util.output import echo


class VariableContainer:
    def __init__(self, variables):
        self.variables = variables
        self.extra_vars = dict()
    
    def set_extra_vars(self, extra_vars):
        self.extra_vars = extra_vars

    def render(self, text):
        variables = {**self.variables, **self.extra_vars}
        result_text = pystache.render(text, variables)
        if result_text.count("{{"):
            raise ConfigurationException("Unresolved variable")
        return result_text

    def get(self, name):
        return self.variables.get(name)

    def has(self, name):
        return name in self.variables


class VariableContainerBuilder:
    def __init__(self, provided_variables):
        self.provided_variables = provided_variables
        self.variables = dict()

    def _read_variable_value_from_file(self, base_path, filename):
        if filename.startswith("vault:"):
            _, key, filename = filename.split(":", 2)
        else:
            key = None
        filename = self.render_value(filename)
        absolute_path = os.path.abspath(os.path.join(base_path, filename))
        with open(absolute_path) as var_file:
            value = var_file.read()
        if key:
            key = self.render_value(key)
            value = decrypt_data(key, value)
        return value

    def _encode_value(self, value, encoder):
        if encoder == "plain":
            return value
        elif encoder == "base64":
            return base64.b64encode(value.encode("utf-8"))
        else:
            raise ConfigurationException("Unknown variable encoder: %s" % encoder)

    def _calculate_variable_value(self, name, config, file_base_path):
        if name in self.provided_variables:
            return self.provided_variables[name]
        if not isinstance(config, dict):
            return config
        env_name = config.get("env")
        if not env_name:
            env_name = "VAR_" + name.replace("-", "_").upper()
        if env_name in os.environ:
            return os.environ[env_name]
        if "file" in config:
            return self._read_variable_value_from_file(file_base_path, config["file"])
        if "default" in config:
            return config["default"]
        return None
    
    def add_variables(self, file_base_path, variable_definitions):
        for name, config in variable_definitions.items():
            if not config:
                config = dict()
            value = self._calculate_variable_value(name, config, file_base_path)
            if not value:
                if config.get("required", False):
                    raise ConfigurationException("Missing required variable %s" % name)
                continue
            if isinstance(config, dict):
                if "values" in config and value not in config["values"]:
                    raise ConfigurationException("Value '%s' not allowed for %s. Possible values: %s"
                                            % (value, name, ','.join(config["values"])))
                if "encode" in config:
                    value = self._encode_value(value, config["encode"])
            self.variables[name] = value
        return self

    def add_direct_variables(self, variables):
        for name, value in variables.items():
            if name in self.variables:
                echo("WARNING!: Variable %s with value '%s' will be overwritten by '%s'" % (name, self.variables[name], value))
            self.variables[name] = value

    def render_value(self, value, extra_vars=dict()):
        if extra_vars:
            variables = {**self.variables, **extra_vars}
        else:
            variables = self.variables
        return pystache.render(value, variables)

    def build(self):
        for name, value in self.provided_variables.items():
            if name not in self.variables:
                self.variables[name] = value
        return VariableContainer(self.variables)

