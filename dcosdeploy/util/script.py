
def run_script(script, entity, variables, entity_variables):
    globals_dict = globals().copy()
    globals_dict["entity"] = entity
    globals_dict["variables"] = variables
    globals_dict["entity_variables"] = entity_variables
    exec(script.replace('\\', '\\\\'), globals_dict, globals_dict)
