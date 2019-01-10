import importlib
import sys
import os
import json
import pystache
import yaml
from ..util import decrypt_data
from ..base import ConfigurationException
from .variables import VariableContainerBuilder


META_NAMES = ["variables", "modules", "includes"]

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
    "dcosdeploy.modules.taskexec",
]


class ConfigHelper(object):
    def __init__(self, variables_container):
        self.variables_container = variables_container

    def set_base_path(self, base_path):
        self.base_path = base_path

    def abspath(self, path):
        return os.path.abspath(os.path.join(self.base_path, path))

    def read_file(self, filename, render_variables=False, as_binary=False):
        if filename.startswith("vault:"):
            _, key, filename = filename.split(":", 2)
        else:
            key = None
        filepath = self.abspath(filename)
        mode = "r"
        if as_binary:
            mode = "rb"
        with open(filepath, mode) as file_obj:
            data = file_obj.read()
        if key:
            data = decrypt_data(key, data)
        if render_variables:
            data = self.variables_container.render(data)
        return data

    def read_yaml(self, filename, render_variables=False):
        return yaml.load(self.read_file(filename, render_variables))

    def read_json(self, filename, render_variables=False):
        return json.loads(self.read_file(filename, render_variables))

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
    config_files = [(abspath, None)]
    idx = 0
    entities = dict()
    variables = VariableContainerBuilder(provided_variables)
    additional_modules = list()

    while idx < len(config_files):
        config_filename, encryption_key = config_files[idx]
        config_basepath = os.path.dirname(config_filename)
        with open(config_filename) as config_file:
            config = config_file.read()
        if encryption_key:
            encryption_key = variables.render_value(encryption_key)
            config = decrypt_data(encryption_key, config)
        config = yaml.load(config)
        variables.add_variables(config_basepath, config.get("variables", dict()))
        for include in config.get("includes", list()):
            if include.startswith("vault:"):
                _, key, include = include.split(":", 2)
            else:
                key = None
            include = variables.render_value(include)
            absolute_include_path = os.path.abspath(os.path.join(config_basepath, include))
            config_files.append((absolute_include_path, key))
        additional_modules.extend(config.get("modules", list()))
        for key, values in config.items():
            if key in META_NAMES:
                continue
            if key in entities:
                raise ConfigurationException("%s found in several files" % key)
            entities[key] = values
            entities[key]["_basepath"] = config_basepath
        idx += 1

    variables = variables.build()
    config_helper = ConfigHelper(variables)
    # init managers
    managers, modules = _init_modules(additional_modules)
    # read config sections
    entities = _read_config_entities(modules, variables, entities, config_helper)
    return entities, managers


def _read_config_entities(modules, variables, config, config_helper):
    deployment_objects = dict()
    for name, entity_config in config.items():
        module = modules[entity_config["type"]]
        parse_config_func = module["parser"]
        preprocess_config_func = module["preprocesser"]
        config_helper.set_base_path(entity_config["_basepath"])
        entities = [(name, entity_config)]
        if preprocess_config_func:
            entities = preprocess_config_func(name, entity_config, config_helper)
        for name, entity_config in entities:
            only_restriction = entity_config.get("only", dict())
            except_restriction = entity_config.get("except", dict())
            when_condition = entity_config.get("when")
            if when_condition and when_condition not in ["dependencies-changed"]:
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


def _check_conditions_apply(variables, restriction_only, restriction_except):
    if restriction_only:
        for var, value in restriction_only.items():
            if not variables.has(var):
                return True
            if isinstance(value, list):
                if variables.get(var) not in value:
                    return True
            elif variables.get(var) != value:
                return True
    if restriction_except:
        for var, value in restriction_except.items():
            if variables.has(var):
                if isinstance(value, list):
                    if variables.get(var) in value:
                        return True
                elif variables.get(var) == value:
                    return True
    return False
