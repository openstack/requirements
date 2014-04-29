#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Copyright 2014 OpenStack Foundation
# Copyright WWW.JD.COM jsonkey@gmail.com  <+86 18551730951>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

'''
Establish pypi source and use nginx pypi source services provided
'''
import os

pypi_domain = 'pypi.example.com'
pypi_source_path = '/var/www'
git_url = 'https://github.com/openstack/requirements'
tmp_path = os.path.join('/tmp', 'openstack_requirements')



def make_dirs(path):
    if not os.path.exists(path):
        os.makedirs(path, mode=0777)
    assert os.path.exists(path), "%s path is not create success"%path

# make pypi source path
make_dirs(path = pypi_source_path)


#-------------------------------------------------------
#
# for clone openstack requirements from github
#
#-------------------------------------------------------
# git clone
# https://github.com/openstack/requirements
make_dirs(path = tmp_path)
cmd = 'cd %(_tmp_path)s && git clone %(_git_url)s'%{'_tmp_path':tmp_path, '_git_url':git_url}
assert 0 == os.system(cmd), "Error execute %s"%cmd

# download pypi from openstack global-requirements.txt
global_requirements_path = os.path.join(tmp_path, "requirements", "global-requirements.txt")

cmd = "pip install pip2pi"
assert 0 == os.system(cmd), "Error execute %s"%cmd

# This may take long time
cmd = 'pip install --no-install  --download=%s -r %s'%(pypi_source_path, global_requirements_path)
assert 0 == os.system(cmd), "Error execute %s"%cmd

# create index
cmd = 'dir2pi %s'%pypi_source_path
assert 0 == os.system(cmd), "Error execute %s"%cmd

#-------------------------------------------------------
#
# config nginx
#
#-------------------------------------------------------
nginx_config ='''
 server {
        listen       80;
        server_name  %s;

        location / {
            root %s;
        }

        error_page   500 502 503 504  /50x.html;
        location = /50x.html {
            root   html;
        }
    }
'''%(pypi_domain, pypi_source_path)
#-------------------------------------------------------
#
# config for pip
#
#-------------------------------------------------------

pip_config_path = '~/.pip/pip.conf'

pip_config = '[global]' \
             'index-url = http://%s/simple'%pypi_domain

print "####"*20
print "nginx config context:"
print nginx_config
print "----"*20
print "pip config path =", pip_config_path
print "----"*20
print "pip config context:"
print pip_config
print "####"*20

if False:
    with open(pip_config_path, w) as fd:
        fd.write(pip_config)
