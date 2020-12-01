import copy
import enum
import importlib
import itertools
import sys
import os
import json
import pystache
import oyaml as yaml
from ..util import decrypt_data, update_dict_with_defaults, md5_hash_str
from ..util.file import check_if_encrypted_is_older
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
    "dcosdeploy.modules.iam_groups",
    "dcosdeploy.modules.iam_users",
    "dcosdeploy.modules.marathon_groups"
]


class ConfigHelper:
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
            check_if_encrypted_is_older(filepath)
            data = decrypt_data(key, data)
        if render_variables:
            data = self.variables_container.render(data)
        return data

    def read_yaml(self, filename, render_variables=False):
        return yaml.safe_load(self.read_file(filename, render_variables))

    def read_json(self, filename, render_variables=False):
        return json.loads(self.read_file(filename, render_variables))

    def render(self, text):
        if text is None:
            return None
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


class EntityContainer:
    def __init__(self, entity, entity_type, dependencies, when_condition, state, pre_script, post_script, entity_variables):
        self.entity = entity
        self.entity_type = entity_type
        self.dependencies = dependencies
        self.reverse_dependencies = list()
        self.when_condition = when_condition
        self.state = state
        self.pre_script = pre_script
        self.post_script = post_script
        self.entity_variables = entity_variables


class EntityScript:
    def __init__(self, apply_script, delete_script):
        self.apply_script = apply_script
        self.delete_script = delete_script


def _parse_entity_script(script, config_helper):
    if not isinstance(script, dict):
        script = dict(apply=script)
    if "apply" in script:
        script["apply"] = config_helper.render(script["apply"])
    if "delete" in script:
        script["delete"] = config_helper.render(script["delete"])
    return EntityScript(script.get("apply"), script.get("delete"))


def _already_in_list(path, config_files):
    for config_filename, _, _, _ in config_files:
        if config_filename == path:
            return True
    return False


def read_config(filenames, provided_variables):
    config_files = [(os.path.abspath(filename), None, None, None) for filename in filenames]
    idx = 0
    entities = dict()
    global_config = dict()
    variables = VariableContainerBuilder(provided_variables)
    variables.add_direct_variables(calculate_predefined_variables())
    additional_modules = list()

    while idx < len(config_files):
        config_filename, encryption_key, only_restriction, except_restriction = config_files[idx]
        config_basepath = os.path.dirname(config_filename)
        with open(config_filename) as config_file:
            config = config_file.read()
        if encryption_key:
            check_if_encrypted_is_older(config_filename)
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
            variables.set_global_vault_key(global_config.get("vault", dict()).get("key"))
        # Read includes
        for include in config.get("includes", list()):
            if isinstance(include, dict):
                filename = include["file"]
                include_only_restriction = include.get("only", None)
                include_except_restriction = include.get("except", None)
            else:
                filename = include
                include_only_restriction = None
                include_except_restriction = None
            if filename.startswith("vault:"):
                if filename.startswith("vault::"):
                    _, filename = filename.split("::", 1)
                    key = DUMMY_GLOBAL_ENCRYPTION_KEY
                else:
                    _, key, filename = filename.split(":", 2)
            else:
                key = None
            filename = variables.render_value(filename)
            absolute_include_path = os.path.abspath(os.path.join(config_basepath, filename))
            if not _already_in_list(absolute_include_path, config_files):
                config_files.append((absolute_include_path, key, include_only_restriction, include_except_restriction))
        # Read extra modules
        additional_modules.extend([(config_basepath, item) for item in config.get("modules", list())])
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
                    if only_restriction:
                        entities[name]["_include_only"] = only_restriction
                    if except_restriction:
                        entities[name]["_include_except"] = except_restriction
            else:
                entities[key] = values
                entities[key]["_basepath"] = config_basepath
                if only_restriction:
                    entities[key]["_include_only"] = only_restriction
                if except_restriction:
                    entities[key]["_include_except"] = except_restriction
        idx += 1

    variables = variables.build()
    config_helper = ConfigHelper(variables, global_config)
    # init managers
    managers, modules = _init_modules(additional_modules)
    # read config sections
    entities = _read_config_entities(modules, variables, entities, config_helper, global_config)
    variables.set_extra_vars(dict()) # Reset extra vars
    return entities, managers, variables


def _read_config_entities(modules, variables, config, config_helper, global_config):
    deployment_objects = dict()
    excluded_entities = list()
    for name, entity_config in config.items():
        entity_type = entity_config["type"]
        module = modules[entity_type]
        parse_config_func = module["parser"]
        preprocess_config_func = module["preprocesser"]
        config_helper.set_base_path(entity_config["_basepath"])
        include_only = entity_config.get("_include_only")
        include_except = entity_config.get("_include_except")
        entities = [(name, entity_config)]
        if preprocess_config_func:
            entities = preprocess_config_func(name, entity_config, config_helper)
        for name, entity_config in entities:
            pre_script = entity_config.get("pre_script")
            post_script = entity_config.get("post_script")
            if pre_script:
                pre_script = _parse_entity_script(pre_script, config_helper)
            if post_script:
                post_script =  _parse_entity_script(post_script, config_helper)
            entity_vars = _prepare_entity_variables(name, entity_config, pre_script, post_script)
            extra_vars = entity_config.get("extra_vars", dict())
            config_helper.set_extra_vars({**extra_vars, **entity_vars})
            if entity_type in global_config:
                update_dict_with_defaults(entity_config, global_config[entity_type])
            only_restriction = entity_config.get("only", dict())
            except_restriction = entity_config.get("except", dict())
            when_condition = entity_config.get("when")
            state = entity_config.get("state")
            if when_condition and when_condition not in ["dependencies-changed"]:
                raise ConfigurationException("Unknown when '%s' for '%s'" % (when_condition, name))
            if _entity_should_be_excluded(variables, include_only, include_except):
                excluded_entities.append(name)
                continue
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
            container = EntityContainer(entity_object, entity_config["type"], dependencies, when_condition, state, pre_script, post_script, entity_vars)
            deployment_objects[name] = container
    _validate_dependencies(deployment_objects, excluded_entities)
    return deployment_objects


def _prepare_entity_variables(name, entity_config, pre_script, post_script):
    entity_vars = dict(_entity_name=name)
    if pre_script:
        if pre_script.apply_script:
            entity_vars["_pre_apply_script_hash"] = md5_hash_str(pre_script.apply_script.encode("utf-8"))
        if pre_script.delete_script:
            entity_vars["_pre_delete_script_hash"] = md5_hash_str(pre_script.delete_script.encode("utf-8"))
    if post_script:
        if post_script.apply_script:
            entity_vars["_post_apply_script_hash"] = md5_hash_str(post_script.apply_script.encode("utf-8"))
        if post_script.delete_script:
            entity_vars["_post_delete_script_hash"] = md5_hash_str(post_script.delete_script.encode("utf-8"))
    return entity_vars


def _init_modules(additional_modules):
    managers = dict()
    modules = dict()
    def _init_module(base_path, module_import):
        if ":" in module_import:
            module_path, module_import = module_import.split(":")
            if base_path:
                module_path = os.path.join(base_path, module_path)
            sys.path.insert(0, module_path)
        module = importlib.import_module(module_import)
        managers[module.__config_name__] = module.__manager__()
        preprocess_config = None
        if "preprocess_config" in module.__dict__:
            preprocess_config = module.preprocess_config
        modules[module.__config_name__] = dict(parser=module.parse_config, preprocesser=preprocess_config)
    for module_import in STANDARD_MODULES:
        _init_module(None, module_import)
    for base_path, module_import in additional_modules:
        _init_module(base_path, module_import)
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
