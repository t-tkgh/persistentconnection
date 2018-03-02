from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
 
import re
import os
import subprocess
import time
import json
import hashlib
from collections import MutableMapping
from ansible import constants as C
from ansible.plugins.callback import CallbackBase
import socket
from datetime import datetime
 
inventory_data = {}
filename_dict = {}
 
#!!Please check this command!!
# $ ansible-config dump
# PERSISTENT_CONTROL_PATH_DIR(default) = /root/.ansible/pc
tmpdir = "/root/.ansible/pc/"
# Please edit connetion alive timeout
timeout = 10
 
jobid = "default"
 
 
class CallbackModule(CallbackBase):
 
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'notification'
    CALLBACK_NAME = 'persistent_connection'
    CALLBACK_NEEDS_WHITELIST = True
 
    TIME_FORMAT = "%b %d %Y %H:%M:%S"
    MSG_FORMAT = "%(now)s - %(category)s - %(data)s\n\n"
 
    def __init__(self):
 
        super(CallbackModule, self).__init__()
 
    def v2_playbook_on_play_start(self, play):
        global inventory_data
        Dict = vars(play._variable_manager)["_hostvars"]
        for index, host in enumerate(Dict):
            inventory_data[index] = Dict.values()[index]
 
    def v2_playbook_on_task_start(self, task, **kwargs):
        global filename_dict
 
        pid = os.getpid()
 
        maxindex = inventory_data.keys()
        for index in maxindex:
            sshport = 22
 
            if "jobid" in str(vars(task._loader)["_FILE_CACHE"].values()[0][0]['vars']):
                jobid = vars(task._loader)["_FILE_CACHE"].values()[
                    0][0]['vars']['jobid']
 
            if "ansible_port" in str(inventory_data[index]):
                sshport = inventory_data[index]['ansible_port']
 
            m = hashlib.sha1()
            m.update((str(inventory_data[index]['inventory_hostname']) + '-'
                     + str(sshport) + '-' + str(vars(task._loader)["_FILE_CACHE"].values()[0][0]['remote_user'])
                     + '-' + 'network_cli' + '-' + str(pid)).encode('utf-8'))
            digest = m.hexdigest()
            cpath = digest[:10]
 
            filename_dict.update({index: {'host': inventory_data[index]['inventory_hostname'],
                 'sshport': sshport, 'remote_user': vars(task._loader)["_FILE_CACHE"].values()[0][0]['remote_user'],
                 'jobid': str(jobid), 'socketfilename': str(cpath)}})
 
            files = os.listdir(tmpdir)
            for file in files:
                pcsocket_path = str(
                    tmpdir) + str(inventory_data[index]['inventory_hostname']) + "_" + str(jobid)
                socketfile = re.compile(
                    str(inventory_data[index]['inventory_hostname']) + "_" + str(jobid))
                if socketfile.search(file):
                    if (datetime.now() - datetime.fromtimestamp(os.stat(str(pcsocket_path)).st_mtime)).seconds < timeout:
                        os.rename(str(pcsocket_path), str(tmpdir) + str(cpath))
                    else:
                        os.remove(str(pcsocket_path))
 
    def v2_runner_on_failed(self, result, ignore_errors=False):
        files = os.listdir(tmpdir)
        for file in files:
            for index in filename_dict.keys():
                socketfile = re.compile(
                    str(filename_dict[index]['socketfilename']))
                if socketfile.search(file):
                    os.rename(str(tmpdir) + str(file), str(tmpdir) + str(
                        filename_dict[index]['host']) + "_" + str(filename_dict[index]['jobid']))
 
    def runner_on_ok(self, host, res):
        files = os.listdir(tmpdir)
        for file in files:
            for index in filename_dict.keys():
                socketfile = re.compile(
                    str(filename_dict[index]['socketfilename']))
                if socketfile.search(file):
                    os.rename(str(tmpdir) + str(file), str(tmpdir) + str(
                        filename_dict[index]['host']) + "_" + str(filename_dict[index]['jobid']))
