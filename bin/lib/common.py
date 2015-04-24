
# work out folder paths, using the location of this file as a base
import os
this_folder = os.path.dirname(os.path.abspath(__file__))
project_root = os.sep.join(str(this_folder).split(os.sep)[:-2])
venv_bin_path = os.sep.join((project_root, 'env', 'dev', 'bin'))


def activate_virtualenv():
    # first, need to check if the venv has been created (does it exist?)
    if not os.path.exists(venv_bin_path):
        # show an error that the user needs to run the bootstrap script first
        print("\n\nCannot find virtualenv for the project.\nHave you run the bootstrap script as required?\n(%s)\n\n" %
              os.sep.join((project_root, 'bootstrap.sh')))
        assert os.path.exists(venv_bin_path), "No virtualenv found"
    # safe to assume we are working alongside a functional virtualenv now
    # now we need to run its activation script
    activate_this = os.sep.join((venv_bin_path, 'activate_this.py'))
    execfile(activate_this, dict(__file__=activate_this))  # @UndefinedVariable
    print("Running from the virtual environment:\n  %s\n" % venv_bin_path)
