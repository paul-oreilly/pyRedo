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

# add some folders to the python path
import sys
sys.path.insert(0, '../')

# first, we activate the virtualenv so that the script can
#    find all the libraries (at the correct versions) via env/dev/
from src.virtualenv import activate_virtualenv, project_root
activate_virtualenv()

# work out some file path information
import os
import time
import shutil
from github import Github
from docopt import docopt
import yaml
import requests
import zipfile
import zlib
from src import yamltools

file_paths = {}
DOMAIN_CONFIG_YAML = 'config.yaml'
DOMAIN_CONFIG_VERSION = 'local-version.yaml'
DOMAIN_FOLDER_FRAGMENT = 'domains'


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
    """
        make a quick copy of the custom sources file
        in case the user wants it later
    """
    timestr = time.strftime("%Y%m%d-%H%M%S")
    shutil.copy(file_paths['custom_sources'],
                os.sep.join((project_root, 'etc', 'custom-sources.backup.%s.yaml' % timestr)))


def add_new_source(args):
    name, url, sha = args['<name>'], args['<url>'], args['--sha']
    # get the current file contents
    # yamltools.read_known_yaml_file('custom_sources')
    file_contents = yamltools.read_yaml_file(file_paths['custom_sources'])
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
        custom_sources.write(yaml.safe_dump(
            _alias_dict_as_list(as_dict), default_flow_style=False))
    print("New information successfully added to %s" % file_paths['custom_sources'])


def remove_source(args):
    name = args['<name>']
    # get the current contents
    file_contents = yamltools.read_yaml_file(file_paths['custom_sources'])
    # see if the file has anything
    if not file_contents:
        print("No custom source list found to alter contents of")
        assert file_contents is not None
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
            """
            with open(file_paths['custom_sources'], 'w') as custom_sources:
                custom_sources.write(yaml.safe_dump(
                    _alias_dict_as_list(as_dict), default_flow_style=False))
            """
            yamltools.write_yaml_file(as_dict, file_paths['custom_sources'], lambda item: item['alias'])
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
    sources_contents = yamltools.read_yaml_file(file_paths['custom_sources'])
    defaults_contents = yamltools.read_yaml_file(file_paths['default_sources'])
    # combine source information
    sources_dict = _contents_to_alias_dict(sources_contents) if sources_contents else {}
    custom_dict = _contents_to_alias_dict(defaults_contents) if defaults_contents else {}
    for k, v in custom_dict.items():
        sources_dict[k] = v
    # make a list of what we need to update
    update_list = []
    if name.lower() == 'all':
        update_list.extend(sources_dict.keys())
    else:
        update_list.append(name)
        # sanity check - do we have a listing for 'name'?
        if not name in sources_dict.keys():
            print("\nUnable to update %s - source with the alias %s was not found.\n" % (name, name))
            assert name in sources_dict.key()
    # for each item to update, we check ...
    #  - What the versions of each should be
    #    Including finding the latest value for each source that autoupdates (has latest as it's version)
    #  - Find out what version we have installed, if any (via [template dir]/local-version.info)
    #  - Make a list of the differences (details, sha sum)
    github_ = Github()
    required_downloads_alias_list = []
    for index, item in enumerate(update_list):
        print("Processing %s (%s/%s)" % (item, index + 1, len(update_list)))
        current_source = sources_dict[item]
        current_source['folder'] = os.sep.join((project_root, DOMAIN_FOLDER_FRAGMENT, current_source['alias']))
        current_source['version_file'] = os.sep.join((current_source['folder'], DOMAIN_CONFIG_VERSION))
        print("  version requirement is %s" % current_source['sha'])
        # check if the local version.info file exists (proxy for 'is it installed?')
        if not os.path.exists(current_source['version_file']):
            current_source['installed'] = False
            print("  not installed")
        else:
            current_source['installed'] = True
            # get the sha of the installed files from the info file, if it exists
            version_file_contents = yamltools.read_yaml_file(current_source['version_file'])
            sha_found = False
            if isinstance(version_file_contents, dict):
                if version_file_contents.get('sha', None):
                    current_source['installed_sha'] = version_file_contents.get('sha')
                    print("  curently installed version is %s" % current_source['installed_sha'])
                    sha_found = True
            if not sha_found:
                print("  version.info file for %s does not contain sha information. Reinstall required." % item)
        # if the 'to install' version is 'latest', we need to find out what the
        #   latest commit on the default branch of the repo is
        # first, we check that the url in the config is a github one
        #  (works for http:// and git:// formats this way)
        print("  url is %s" % current_source['repo'])
        if not 'github.com' in current_source['repo'].lower():
            print("  %s is not a github repo url\n  (currently, only github repo's are supported)" % item)
        else:
            if current_source['sha'].lower() == 'latest':
                print("  looking up github information for %s" % item)
                github_address = '/'.join(current_source['repo'].split('/')[-2:])
                print("    (%s)" % github_address)
                current_source['github_address'] = github_address
                print("    looking up repository")
                repo = github_.get_repo(github_address)
                print("    finding the default branch")
                default_branch = repo.get_branch(repo.default_branch)
                print("    latest commit: %s " % default_branch.commit.sha)
                current_source['latest_commit'] = default_branch.commit.sha
                update_required = False
                if not 'installed_sha' in current_source.keys():
                    print("    no version currently installed.\n    update required")
                    update_required = True
                elif current_source['installed_sha'] != current_source['latest_commit']:
                    print("    local installed version is out of date.\n    update required")
                    update_required = True
                if update_required:
                    current_source['download'] = "https://github.com/{github_address}/archive/{sha}.zip".format(
                        github_address=github_address, sha=current_source['latest_commit'])
                    print('    download url: %s' % current_source['download'])
                    required_downloads_alias_list.append(current_source['alias'])
    # now we know which (if any) items need a new download (in required_downloads_alias_list)
    #  we can check and see if we have the file downloaded already, and if not, download it.
    # first, quick sanity check to make sure the .cache directory exists
    downloads_temp_directory = os.path.sep.join((project_root, '.tmp', 'downloads'))
    if not os.path.exists(downloads_temp_directory):
        os.makedirs(downloads_temp_directory)
    # it would also be a good point to make sure the templates directory exists too
    sources_directory = os.path.sep.join((project_root, DOMAIN_FOLDER_FRAGMENT))
    if not os.path.exists(sources_directory):
        os.makedirs(sources_directory)
    # see if we have any further work to do
    if len(required_downloads_alias_list) == 0:
        print("\nNo updates are required.")
        return
    # download and update template dirs as required
    print("\n\n%s potential updates found." % len(required_downloads_alias_list))
    for i, alias in enumerate(required_downloads_alias_list):
        current_source = sources_dict[alias]
        print("  checking updates for %s (%s/%s)" % (alias, i + 1, len(required_downloads_alias_list)))
        # get a url to the download file location on github
        print("  obtaining download url")
        remote_file_location = requests.head(current_source['download']).headers['location']
        print("    %s" % remote_file_location)
        save_file_name = '-'.join((current_source['github_address'].replace('/', '-'),
                                   current_source['latest_commit'])) + '.zip'
        save_file_location = os.path.sep.join((downloads_temp_directory, save_file_name))
        with open(save_file_location, 'w') as cache_file:
            print("  downloading file %s" % current_source['download'])
            cache_file.write(requests.get(current_source['download']).content)
            print("  file saved as %s" % save_file_name)
        # TODO: Complete function
        # remove the contents of any existing template dir
        current_template_directory = os.path.sep.join((sources_directory, alias))
        if os.path.exists(current_template_directory):
            shutil.rmtree(current_template_directory)
        # create a new empty dir
        os.makedirs(current_template_directory)
        # unzip the file to the sources directory
        print("  extracting files")
        top_level_replacement = '-'.join((current_source['repo'].split('/')[-1],
                                          current_source['latest_commit']))
        top_level_replacement = [top_level_replacement + '/', top_level_replacement + '\\']
        with zipfile.ZipFile(save_file_location, 'r') as current_zip:
            for item in current_zip.namelist():
                # skip over directories in the zip file
                # TODO: binary file support - whitelist text filetypes or check encoding
                if not (item[-1] == '\\' or item[-1] == '/'):
                    #    github's archive format is a top level folder with the full name (inc sha sum)
                    #    we take the contents of that folder, and extract it into templates/[alias]/
                    with current_zip.open(item, 'rU') as current_zip_file:
                        output_filename = item
                        for replacement in top_level_replacement:
                            output_filename = output_filename.replace(replacement, '')
                        output_filepath = os.path.sep.join((current_template_directory, output_filename))
                        # make sure any required directory is present
                        if not os.path.exists(os.path.dirname(output_filepath)):
                            os.makedirs(os.path.dirname(output_filepath))
                        # write to the target file
                        with open(output_filepath, 'w') as target_file:
                            target_file.write(current_zip_file.read())
        # TODO: Write a local-version.yaml file with source info, sha sum etc
        local_version_info = {'source': current_source['repo'], 'sha': current_source['latest_commit']}
        yamltools.write_yaml_file(local_version_info, current_source['version_file'])
    # clean up - remove any downloaded files in .cache
    shutil.rmtree(downloads_temp_directory)


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
    # setup some basic information
    file_paths['default_sources'] = os.sep.join((project_root, 'etc', 'default-sources.yaml'))
    file_paths['custom_sources'] = os.sep.join((project_root, 'etc', 'custom-sources.yaml'))
    resolve_arg(args, arg_map)
