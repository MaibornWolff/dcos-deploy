from .file import read_yaml


def get_variables(variables):
    provided_variables = dict()
    for variable in variables:
        if variable[0] == "@":
            for name, value in read_yaml(variable[1:]).items():
                provided_variables[name] = value
            continue
        if "=" not in variable:
            raise Exception("No value defined for %s" % variable)
        name, value = variable.split("=", 1)
        provided_variables[name] = value
    return provided_variables
