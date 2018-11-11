import importlib
import sys
import os
import json
import pystache
import yaml
from .util import read_yaml
from .base import ConfigurationException


STANDARD_MODULES = [
    "dcosdeploy.modules.accounts",
    "dcosdeploy.modules.secrets",
    "dcosdeploy.modules.jobs",
    "dcosdeploy.modules.apps",
    "dcosdeploy.modules.frameworks",
    "dcosdeploy.modules.certs",
    "dcosdeploy.modules.repositories",
    "dcosdeploy.modules.edgelb",
    "dcosdeploy.modules.s3",
]


class VariableContainer(object):
    def __init__(self, variables):
        self.variables = variables

    def render(self, text, extra_vars=dict()):
        if extra_vars:
            variables = {**self.variables, **extra_vars}
        else:
            variables = self.variables
        result_text = pystache.render(text, variables)
        if result_text.count("{{"):
            raise ConfigurationException("Unresolved variable")
        return result_text

    def get(self, name):
        return self.variables.get(name)

    def has(self, name):
        return name in self.variables


class ConfigHelper(object):
    def __init__(self, variables_container, base_path):
        self.variables_container = variables_container
        self.base_path = base_path

    def abspath(self, path):
        return os.path.abspath(os.path.join(self.base_path, path))

    def read_file(self, filename, render_variables=False):
        filepath = self.abspath(filename)
        with open(filepath) as file_obj:
            data = file_obj.read()
        if render_variables:
            data = self.variables_container.render(data)
        return data

    def read_yaml(self, filename, render_variables=False):
        return yaml.load(self.read_file(filename))

    def read_json(self, filename, render_variables=False):
        return json.loads(self.read_file(filename))

    def render(self, text, extra_vars=dict()):
        return self.variables_container.render(text, extra_vars)


class EntityContainer(object):
    def __init__(self, entity, entity_type, dependencies, when_condition):
        self.entity = entity
        self.entity_type = entity_type
        self.dependencies = dependencies
        self.when_condition = when_condition


def read_config(filename, provided_variables):
    abspath = os.path.abspath(filename)
    base_path = os.path.dirname(abspath)
    config = read_yaml(abspath)
    variables = _read_variables(config.get("variables", dict()), provided_variables)
    config_helper = ConfigHelper(variables, base_path)
    for include in config.get("includes", list()):
        absolute_include_path = os.path.abspath(os.path.join(base_path, include))
        additional_configs = read_yaml(absolute_include_path)
        for key, values in additional_configs.items():
            if key in config:
                raise ConfigurationException("%s found in base config and include file %s" % (key, include))
            config[key] = values
    # init managers
    additional_modules = config.get("modules", list())
    managers, modules = _init_modules(additional_modules)
    # read config sections
    entities = _read_config_entities(modules, variables, config, config_helper)
    return entities, managers


def _read_config_entities(modules, variables, config, config_helper):
    deployment_objects = dict()
    for name, entity_config in config.items():
        if name in ["variables", "modules", "includes"]:
            continue
        module = modules[entity_config["type"]]
        parse_config_func = module["parser"]
        preprocess_config_func = module["preprocesser"]
        entities = [(name, entity_config)]
        if preprocess_config_func:
            entities = preprocess_config_func(name, entity_config, config_helper)
        for name, entity_config in entities:
            only_restriction = entity_config.get("only", dict())
            except_restriction = entity_config.get("except", dict())
            when_condition = entity_config.get("when")
            if when_condition and when_condition not in ["dependencies-updated"]:
                raise ConfigurationException("Unknown when '%s' for '%s'" % (when_condition, name))
            if _check_conditions_apply(variables, only_restriction, except_restriction):
                continue
            dependencies_config = entity_config.get("dependencies", list())
            entity_object = parse_config_func(name, entity_config, config_helper)
            dependencies = list()
            for dependency in dependencies_config:
                if dependency.count(":") > 0:
                    dependency, dep_type = dependency.rsplit(":", 1)
                else:
                    dep_type = "create"
                dependencies.append((dependency, dep_type))
            container = EntityContainer(entity_object, entity_config["type"], dependencies, when_condition)
            deployment_objects[name] = container
    _validate_dependencies(deployment_objects)
    return deployment_objects


def _init_modules(additional_modules):
    managers = dict()
    modules = dict()
    for module_path in STANDARD_MODULES + additional_modules:
        if ":" in module_path:
            base_path, module_path = module_path.split(":")
            sys.path.insert(0, base_path)
        module = importlib.import_module(module_path)
        managers[module.__config_name__] = module.__manager__()
        preprocess_config = None
        if "preprocess_config" in module.__dict__:
            preprocess_config = module.preprocess_config
        modules[module.__config_name__] = dict(parser=module.parse_config, preprocesser=preprocess_config)
    return managers, modules


def _validate_dependencies(entities):
    for name, entity in entities.items():
        for dependency, dep_type in entity.dependencies:
            if dependency not in entities:
                raise ConfigurationException("Unknown entity '%s' as dependency in '%s'" % (dependency, name))


def _calculate_variable_value(name, config, provided_variables):
    if name in provided_variables:
        return provided_variables[name]
    env_name = config.get("from")
    if not env_name:
        env_name = "VAR_" + name.replace("-", "_").upper()
    if env_name in os.environ:
        return os.environ[env_name]
    if "default" in config:
        return config["default"]
    return None


def _read_variables(variables, provided_variables):
    resulting_variables = dict()
    for name, config in variables.items():
        value = _calculate_variable_value(name, config, provided_variables)
        if not value and config.get("required", False):
            raise ConfigurationException("Missing required variable %s" % name)
        if "values" in config and value not in config["values"]:
            raise ConfigurationException("Value '%s' not allowed for %s. Possible values: %s"
                                         % (value, name, ','.join(config["values"])))
        resulting_variables[name] = value
    for name, value in provided_variables.items():
        if name not in resulting_variables:
            resulting_variables[name] = value
    return VariableContainer(resulting_variables)


def _check_conditions_apply(variables, restriction_only, restriction_except):
    if restriction_only:
        for var, value in restriction_only.items():
            if not variables.has(var):
                return True
            if variables.get(var) != value:
                return True
    if restriction_except:
        for var, value in restriction_except.items():
            if variables.has(var) and variables.get(var) == value:
                return True
    return False
