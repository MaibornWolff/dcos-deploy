import importlib
import sys
import pystache
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


def read_config(filename, provided_variables):
    config = read_yaml(filename)
    variables = _read_variables(config.get("variables", dict()), provided_variables)
    for include in config.get("includes", list()):
        additional_configs = read_yaml(include)
        for key, values in additional_configs.items():
            if key in config:
                raise ConfigurationException("%s found in base config and include file %s" % (key, include))
            config[key] = values
    # init managers
    additional_modules = config.get("modules", list())
    managers, modules = _init_modules(additional_modules)
    # read config sections
    deployment_objects, dependencies = _read_config_entities(modules, variables, config)
    return deployment_objects, dependencies, managers


def _read_config_entities(modules, variables, config):
    deployment_objects = dict()
    deployment_dependencies = dict()
    for name, entity_config in config.items():
        if name in ["variables", "modules", "includes"]:
            continue
        module = modules[entity_config["type"]]
        parse_config_func = module["parser"]
        preprocess_config_func = module["preprocesser"]
        entities = [(name, entity_config)]
        if preprocess_config_func:
            entities = preprocess_config_func(name, entity_config)
        for name, entity_config in entities:
            only_restriction = entity_config.get("only", dict())
            except_restriction = entity_config.get("except", dict())
            if _check_conditions_apply(variables, only_restriction, except_restriction):
                continue
            dependencies = entity_config.get("dependencies", None)
            deployment_object = parse_config_func(name, entity_config, variables)
            if dependencies:
                deployment_dependencies[name] = dependencies
            deployment_objects[name] = deployment_object
    dependencies = _build_dependency_tree(deployment_dependencies, deployment_objects)
    return deployment_objects, dependencies


def _init_modules(additional_modules):
    managers = dict()
    modules = dict()
    for module_path in STANDARD_MODULES + additional_modules:
        if ":" in module_path:
            base_path, module_path = module_path.split(":")
            sys.path.insert(0, base_path)
        module = importlib.import_module(module_path)
        managers[module.__config__] = module.__manager__()
        preprocess_config = None
        if "preprocess_config" in module.__dict__:
            preprocess_config = module.preprocess_config
        modules[module.__config_name__] = dict(parser=module.parse_config, preprocesser=preprocess_config)
    return managers, modules


def _build_dependency_tree(dependencies_map, config):
    resulting_dependencies = dict()
    for name, string_dependencies in dependencies_map.items():
        dependencies = list()
        for dependency in string_dependencies:
            if dependency.count(":") > 0:
                dependency, dep_type = dependency.rsplit(":", 1)
            else:
                dep_type = "create"
            dependency_object = config.get(dependency)
            if not dependency_object:
                raise Exception("Could not find %s" % dependency)
            dependencies.append((dependency, dependency_object, dep_type))
        resulting_dependencies[name] = dependencies
    return resulting_dependencies


def _read_variables(variables, provided_variables):
    resulting_variables = dict()
    for name, config in variables.items():
        if config.get("required", False) and name not in provided_variables:
            raise ConfigurationException("Missing required variable %s" % name)
        if name not in provided_variables:
            if "default" in config:
                resulting_variables[name] = config["default"]
        else:
            if "values" in config:
                if provided_variables[name] not in config["values"]:
                    raise ConfigurationException("Value '%s' not allowed for %s. Possible values: %s"
                                                 % (provided_variables[name], name, ','.join(config["values"])))
            resulting_variables[name] = provided_variables[name]
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
