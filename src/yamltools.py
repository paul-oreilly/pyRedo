
import os
import yaml

# TODO: Convert all yaml file reads to this function (no dict state use)


def read_yaml_file(file_path):
    if not os.path.exists(file_path):
        return None
    else:
        with open(file_path, 'r') as current_file:
            try:
                contents = yaml.safe_load(current_file)
                return contents
            except yaml.YAMLError as exc:
                if hasattr(exc, 'problem_mark'):
                    mark = exc.problem_mark
                    print("Error in yaml file (%s)\nline %s, column %s" %
                          (exc, mark.line + 1, mark.column + 1))
                else:
                    print("Unknown error in yaml file %s" % exc)
                return None


def write_yaml_file(contents, file_path, sort_func=None):
    """
    Writes contents to the given file_path
    Support for sorting via sort_func (takes 1 parameter, item, returns sorting key)
    """
    # if type(contents) is dict:
    #    contents = [contents]
    with open(file_path, 'w') as yaml_output:
        if sort_func:
            yaml_output.write(yaml.safe_dump(
                sorted(contents, key=sort_func), default_flow_style=False))
        else:
            yaml_output.write(yaml.safe_dump(contents, default_flow_style=False))
