import copy
import enum
import importlib
import itertools
import sys
import os
import json
import pystache
import oyaml as yaml
from ..util import decrypt_data, update_dict_with_defaults
from ..base import ConfigurationException
from .variables import VariableContainerBuilder
from .predefined import calculate_predefined_variables


META_NAMES = ["variables", "modules", "includes", "global"]
DUMMY_GLOBAL_ENCRYPTION_KEY = "__global__"

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
    "dcosdeploy.modules.httpcall",
]


class ConfigHelper(object):
    def __init__(self, variables_container, global_config):
        self.variables_container = variables_container
        self.global_config = global_config

    def set_base_path(self, base_path):
        self.base_path = base_path
    
    def set_extra_vars(self, extra_vars):
        self.variables_container.set_extra_vars(self.prepare_extra_vars(extra_vars))

    def abspath(self, path):
        return os.path.abspath(os.path.join(self.base_path, path))

    def read_file(self, filename, render_variables=False, as_binary=False):
        if filename.startswith("vault:"):
            if filename.startswith("vault::"):
                if not self.global_config or "vault" not in self.global_config or "key" not in self.global_config["vault"]:
                    raise ConfigurationException("vault definition without key but no key is defined in global config: %s" % filename)
                _, filename = filename.split("::", 1)
                key = self.variables_container.render(self.global_config["vault"]["key"])
            else:
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
        return yaml.safe_load(self.read_file(filename, render_variables))

    def read_json(self, filename, render_variables=False):
        return json.loads(self.read_file(filename, render_variables))

    def render(self, text):
        return self.variables_container.render(text)

    def prepare_extra_vars(self, extra_vars):
        return dict(self._prepare_extra_vars_inner(extra_vars))

    def _prepare_extra_vars_inner(self, extra_vars):
        for key, value in extra_vars.items():
            if ":" in key:
                var, var_equal_value = key.split(":", 1)
                var_value = self.variables_container.get(var)
                if not var_value:
                    raise ConfigurationException("Variable %s is not defined. Can not be used in extra_vars" % var)
                if var_value == var_equal_value:
                    for sub_key, sub_value in self._prepare_extra_vars_inner(value):
                        yield sub_key, sub_value
            else:
                yield (key, value)


class StateEnum(enum.Enum):
    NONE = 0
    REMOVED = 1

    @staticmethod
    def convert(name):
        if not name:
            return StateEnum.NONE
        elif name.lower() == "removed":
            return StateEnum.REMOVED
        else:
            raise ConfigurationException("Unknown state value '%s'" % name)


class EntityContainer(object):
    def __init__(self, entity, entity_type, dependencies, when_condition, state):
        self.entity = entity
        self.entity_type = entity_type
        self.dependencies = dependencies
        self.reverse_dependencies = list()
        self.when_condition = when_condition
        self.state = state


def read_config(filename, provided_variables):
    abspath = os.path.abspath(filename)
    config_files = [(abspath, None)]
    idx = 0
    entities = dict()
    global_config = dict()
    variables = VariableContainerBuilder(provided_variables)
    additional_modules = list()

    while idx < len(config_files):
        config_filename, encryption_key = config_files[idx]
        config_basepath = os.path.dirname(config_filename)
        with open(config_filename) as config_file:
            config = config_file.read()
        if encryption_key:
            if encryption_key == DUMMY_GLOBAL_ENCRYPTION_KEY:
                if not global_config or "vault" not in global_config or "key" not in global_config["vault"]:
                    raise ConfigurationException("vault definition without key but no key is defined in global config: %s" % config_filename)
                encryption_key = global_config["vault"]["key"]
            encryption_key = variables.render_value(encryption_key)
            config = decrypt_data(encryption_key, config)
        config = yaml.safe_load(config)
        # Read variables
        variables.add_variables(config_basepath, config.get("variables", dict()))
        # Read global config
        if "global" in config:
            if global_config:
                raise ConfigurationException("Only one global configuration can exist")
            global_config = config["global"]
        # Read includes
        for include in config.get("includes", list()):
            if include.startswith("vault:"):
                if include.startswith("vault::"):
                    _, include = include.split("::", 1)
                    key = DUMMY_GLOBAL_ENCRYPTION_KEY
                else:
                    _, key, include = include.split(":", 2)
            else:
                key = None
            include = variables.render_value(include)
            absolute_include_path = os.path.abspath(os.path.join(config_basepath, include))
            if (absolute_include_path, key) not in config_files:
                config_files.append((absolute_include_path, key))
        # Read extra modules
        additional_modules.extend(config.get("modules", list()))
        # Read entities
        for key, values in config.items():
            if key in META_NAMES:
                continue
            if key in entities:
                raise ConfigurationException("%s found in several files" % key)
            if "loop" in values:
                for name, value in _expand_loop(key, values):
                    if name in entities:
                        raise ConfigurationException("%s found in several files" % name)
                    entities[name] = value
                    entities[name]["_basepath"] = config_basepath
            else:
                entities[key] = values
                entities[key]["_basepath"] = config_basepath
        idx += 1

    variables.add_direct_variables(calculate_predefined_variables())
    variables = variables.build()
    config_helper = ConfigHelper(variables, global_config)
    # init managers
    managers, modules = _init_modules(additional_modules)
    # read config sections
    entities = _read_config_entities(modules, variables, entities, config_helper, global_config)
    return entities, managers


def _read_config_entities(modules, variables, config, config_helper, global_config):
    deployment_objects = dict()
    excluded_entities = list()
    for name, entity_config in config.items():
        entity_type = entity_config["type"]
        module = modules[entity_type]
        parse_config_func = module["parser"]
        preprocess_config_func = module["preprocesser"]
        config_helper.set_base_path(entity_config["_basepath"])
        entities = [(name, entity_config)]
        if preprocess_config_func:
            entities = preprocess_config_func(name, entity_config, config_helper)
        for name, entity_config in entities:
            config_helper.set_extra_vars(entity_config.get("extra_vars", dict()))
            if entity_type in global_config:
                update_dict_with_defaults(entity_config, global_config[entity_type])
            only_restriction = entity_config.get("only", dict())
            except_restriction = entity_config.get("except", dict())
            when_condition = entity_config.get("when")
            state = entity_config.get("state")
            if when_condition and when_condition not in ["dependencies-changed"]:
                raise ConfigurationException("Unknown when '%s' for '%s'" % (when_condition, name))
            if _entity_should_be_excluded(variables, only_restriction, except_restriction):
                excluded_entities.append(name)
                continue
            if state and state not in ["removed"]:
                raise ConfigurationException("Unknown state '%s for '%s" % (state, name))
            state = StateEnum.convert(state)
            dependencies_config = entity_config.get("dependencies", list())
            entity_object = parse_config_func(name, entity_config, config_helper)
            dependencies = list()
            for dependency in dependencies_config:
                if dependency.count(":") > 0:
                    dependency, dep_type = dependency.rsplit(":", 1)
                else:
                    dep_type = "create"
                dependencies.append((dependency, dep_type))
            container = EntityContainer(entity_object, entity_config["type"], dependencies, when_condition, state)
            deployment_objects[name] = container
    _validate_dependencies(deployment_objects, excluded_entities)
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


def _validate_dependencies(entities, excluded_entities):
    for name, entity in entities.items():
        # Remove all dependencies for entities that were excluded (based on only/except restrictions)
        entity.dependencies = [dep for dep in entity.dependencies if dep[0] not in excluded_entities]
        for dependency, _ in entity.dependencies:
            if dependency not in entities:
                raise ConfigurationException("Unknown entity '%s' as dependency in '%s'" % (dependency, name))


def _entity_should_be_excluded(variables, restriction_only, restriction_except):
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


def _expand_loop(key, values):
    loop = values["loop"]
    del values["loop"]
    extra_vars = values.get("extra_vars", dict())
    loop_vars = loop.keys()
    if "{{" in key:
        name_template = key
    else:
        name_template = "%s-%s" % (key, '-'.join(["{{%s}}" % var for var in loop_vars]))
    for combination in itertools.product(*[loop[var] for var in loop_vars]):
        variables = {**extra_vars, **dict([(var, combination[idx]) for idx, var in enumerate(loop_vars)])}
        name = pystache.render(name_template, variables)
        entity_config = copy.deepcopy(values)
        entity_config["extra_vars"] = variables
        yield name, entity_config
