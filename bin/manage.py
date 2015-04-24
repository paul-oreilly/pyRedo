#!/usr/bin/env python2
"""Usage:
    manage.py source add git <name> <url> [--sha=<git-hash>]
    manage.py source remove <name>
    manage.py source remove all
    manage.py source list default|custom|all
    manage.py source update <name> [--no-render]
    manage.py source update all    [--no-render]
    manage.py render <name> [--all] [--filter=<filters>]
    manage.py render all [--all] [--filter=<filters>]

Options:
    -h --help            Show this screen.
    --version            Show version.
    --sha=<git-hash>     The sha hash pointing to a specific version of the repository to checkout [default: latest]
    --all         .      Process every template (not just updated or new ones)
    [--filter=<filters]  Comma seperated list of renderers to run (eg to only create .py classes, or just pdf's etc) [default: all]
    --no-render          Only download template file updates, no further processing or rendering of changes
"""

# TODO: Check duplicate functions for custom sources
# TODO: A save function for custom_sources that stores them in order by alias

#from bin import activate_virtualenv
from lib.common import activate_virtualenv, project_root
activate_virtualenv()

# work out some file path information
import os
file_paths = {'default_sources': os.sep.join((project_root, 'etc', 'default-sources.yaml')),
              'custom_sources': os.sep.join((project_root, 'etc', 'custom-sources.yaml'))}
file_contents = {}


from docopt import docopt
import yaml
import time
import shutil


def read_yaml_file(name):
    # if there's no file yet, we need to create one
    if not os.path.exists(file_paths[name]):
        # by 'open.close', we ensure there will be a file left there
        open(file_paths[name], 'a').close()
    # try and read the contents of the file
    with open(file_paths[name], 'r') as current_file:
        try:
            contents = yaml.safe_load(current_file)
            file_contents[name] = contents
        except yaml.YAMLError as exc:
            if hasattr(exc, 'problem_mark'):
                mark = exc.problem_mark
                print("Error in yaml file (%s)\nline %s, column %s" % (exc, mark.line + 1, mark.column + 1))
            else:
                print("Unknown error in yaml file %s" % exc)
            return None


def _contents_to_alias_dict(contents):
    contents_dict = {}
    for item in contents:
        key = dict(item).get('alias', None)
        if key:
            contents_dict[key] = item
    return contents_dict


def _alias_dict_as_list(alias_dict):
    return_list = []
    for key in sorted(alias_dict.keys()):
        return_list.append(alias_dict[key])
    return return_list


def _backup_custom_sources():
    """ make a quick copy of the custom sources file in case the user wants it later """
    timestr = time.strftime("%Y%m%d-%H%M%S")
    shutil.copy(file_paths['custom_sources'], os.sep.join((project_root, 'etc', 'custom-sources.backup.%s.yaml' % timestr)))


def add_new_source(args):
    name, url, sha = args['<name>'], args['<url>'], args['--sha']
    # get the current file contents
    read_yaml_file('custom_sources')
    # add the new information
    if not file_contents['custom_sources']:
        file_contents['custom_sources'] = []
    # convert contents to a dict, so we can alter it easier
    as_dict = _contents_to_alias_dict(file_contents['custom_sources'])
    # write the new information
    as_dict[name] = {'alias': name, 'repo': url, 'sha': sha}
    # wipe the old information
    del file_contents['custom_sources']
    # write the output
    _backup_custom_sources()
    with open(file_paths['custom_sources'], 'w') as custom_sources:
        custom_sources.write(yaml.safe_dump(_alias_dict_as_list(as_dict), default_flow_style=False))
    print("New information successfully added to %s" % file_paths['custom_sources'])


def remove_source(args):
    name = args['<name>']
    # get the current contents
    read_yaml_file('custom_sources')
    # see if the file has anything
    if not file_contents['custom_sources']:
        print("No custom source list found to alter contents of")
        assert file_contents['custom_sources'] is not None
    # special behavior if the name is 'all'
    if name == 'all':
        # reset the file
        _backup_custom_sources()
        open(file_paths['custom_sources'], 'w').close()
        print("All entries removed from custom_sources")
    else:
        # convert to dict
        as_dict = _contents_to_alias_dict(file_contents['custom_sources'])
        # check for the key
        if name in as_dict.keys():
            del as_dict[name]
            _backup_custom_sources()
            with open(file_paths['custom_sources'], 'w') as custom_sources:
                custom_sources.write(yaml.safe_dump(_alias_dict_as_list(as_dict), default_flow_style=False))
            print("Removed %s from custom sources (%s)" % (name, file_paths['custom_sources']))
        else:
            print("\'%s\' is not a valid alias found in %s" % (name, file_paths['custom_sources']))


def update_sources(args):
    # TODO: Check each source for updates
    # Download any new templates
    # Unless --no-render has been set, call the rendering functions to update
    #  changes caused by the new files
    name = args['<name>']
    if name.lower() == 'all':
        print("Updating all sources")
    else:
        print("Updating source %s" % name)
    read_yaml_file('custom_sources')
    read_yaml_file('default_sources')
    all_sources = []
    # TODO: Check order of below, ensure that custom information overrides default.
    if file_contents['default_sources']:
        all_sources.extend(file_contents['default_sources'])
    if file_contents['custom_sources']:
        all_sources.extend(file_contents['custom_sources'])
    # TODO: Complete function


def source_functions_handler(args):
    # TODO: Add listing support
    source_subfuncs = {'add': add_new_source, 'remove': remove_source,
                       'update': update_sources}
    resolve_arg(args, source_subfuncs)


def resolve_arg(args, arg_map):
    for key in arg_map.keys():
        if args[key]:
            arg_map[key](args)


arg_map = {'source': source_functions_handler}

if __name__ == '__main__':
    args = docopt(__doc__, version='PyRedo 0.1-dev')
    resolve_arg(args, arg_map)
