
# Create virtual env

```
cd tap-kustomer
pyenv install 3.5.2 # if needed
pyenv local 3.5.2
pyenv virtualenvwrapper_lazy
mkvirtualenv tap-kustomer
```

  OR: 
  
```
mkvirtualenv -p **PATH_TO**.pyenv/versions/3.5.2/bin/python3 tap-kustomer
```
```
workon tap-kustomer
```
​
# pip installs w/in virtualenv

```
pip install --upgrade pip
pip install singer-tools
pip install singer-python
pip install requests
pip install backoff
pip install ipykernel
pip install pylint
python -m ipykernel install --user --name tap-kustomer --display-name "Python (tap-kustomer)"
```
​
​
**For personal tap, git clone and add upstream remote: https://help.github.com/en/articles/configuring-a-remote-for-a-fork**

```
cd ~/code/bytecode/Stitch/personal_forks
git clone https://github.com/jeffhuth-bytecode/tap-kustomer.git
cd tap-kustomer
git remote -v
git remote add upstream https://github.com/singer-io/tap-kustomer.git
git remote -v
# Sync personal fork with upstream: https://help.github.com/en/articles/syncing-a-fork
git fetch upstream
git checkout master
git merge upstream/master
```
​
# Run in tap and target virtualenvs 
# general discover

```
~/.virtualenvs/tap-kustomer/bin/tap-kustomer --config ~/code/bytecode/Stitch/tap-kustomer/tap_kustomer/tap_config.json --discover > catalog.json
```
​
# singer-discover

```
~/.virtualenvs/tap-kustomer/bin/tap-kustomer --config ~/code/bytecode/Stitch/tap-kustomer/tap_kustomer/tap_config.json --discover | ~/.virtualenvs/singer-discover/bin/singer-discover -o ~/code/bytecode/Stitch/tap-kustomer/catalog.json
```
​
# singer-check-tap

```
~/.virtualenvs/tap-kustomer/bin/tap-kustomer --config ~/code/bytecode/Stitch/tap-kustomer/tap_kustomer/tap_config.json --catalog ~/code/bytecode/Stitch/tap-kustomer/catalog.json | ~/.virtualenvs/tap-kustomer/bin/singer-check-tap  > ~/code/bytecode/Stitch/tap-kustomer/state.json
```
​
# target-stitch initial load - dry-run

```
~/.virtualenvs/tap-kustomer/bin/tap-kustomer --config ~/code/bytecode/Stitch/tap-kustomer/tap_kustomer/tap_config.json --catalog ~/code/bytecode/Stitch/tap-kustomer/catalog.json | ~/.virtualenvs/target-stitch/bin/target-stitch --config ~/code/bytecode/Stitch/tap-kustomer/tap_kustomer/target_config.json --dry-run > ~/code/bytecode/Stitch/tap-kustomer/state.json
```
​
# target-stitch initial load

```
~/.virtualenvs/tap-kustomer/bin/tap-kustomer --config ~/code/bytecode/Stitch/tap-kustomer/tap_kustomer/tap_config.json --catalog ~/code/bytecode/Stitch/tap-kustomer/catalog.json | ~/.virtualenvs/target-stitch/bin/target-stitch --config ~/code/bytecode/Stitch/tap-kustomer/tap_kustomer/target_config.json > ~/code/bytecode/Stitch/tap-kustomer/state.json
```
​
# target-stitch incremental load (state_previous.json)

```
~/.virtualenvs/tap-kustomer/bin/tap-kustomer --config ~/code/bytecode/Stitch/tap-kustomer/tap_kustomer/tap_config.json --catalog ~/code/bytecode/Stitch/tap-kustomer/catalog.json --state ~/code/bytecode/Stitch/tap-kustomer/state_previous.json | ~/.virtualenvs/target-stitch/bin/target-stitch --config ~/code/bytecode/Stitch/tap-kustomer/tap_kustomer/target_config.json > ~/code/bytecode/Stitch/tap-kustomer/state.json
```
​
# pylint

```
pylint tap_kustomer -d missing-docstring -d logging-format-interpolation -d too-many-locals -d too-many-arguments
```
