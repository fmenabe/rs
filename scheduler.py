#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import datetime
import signal
import multiprocessing
import subprocess
import socket

# Set Django environement.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
from rs.models  import Hosts, Schedules

USAGE = 'scheduler.py <start|stop|reload|status>'
PID_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'run')

class SignalException(Exception):
    pass


class ConfigManager(multiprocessing.Process):
    def __init__(self, config):
        multiprocessing.Process.__init__(self)
        self.name = 'rs_config'
        self.config = config


    def load(self):
#        print "loading configuration"
        hosts = dict((
            (host.id, host.fqdn) \
            for host in Hosts.objects.all()
        ))
        schedules = dict((
            (schedule.host_id,
                (
                    schedule.hours,
                    schedule.minutes,
                    schedule.dom,
                    schedule.mon,
                    schedule.dow,
                    schedule.path
                )
            ) for schedule in Schedules.objects.all()
        ))
        self.config['hosts'] = hosts
        self.config['schedules'] = schedules


    def run(self):
        while True:
            self.load()
            time.sleep(5)


class TasksManager(multiprocessing.Process):
    def __init__(self, config, pids):
        multiprocessing.Process.__init__(self)
        self.name = 'rs_scheduler'
        self.config = config
        self.pids = pids


    def run(self):
        while True:
#            print 'config: %s' % self.config
            time.sleep(5)


class ManagerServer(multiprocessing.Process):
    def __init__(self):
        multiprocessing.Process.__init__(self)
        self.name = 'rs_manager'
        self.config = multiprocessing.Manager().dict()
        self.pids = multiprocessing.Manager().dict()



    def run(self):
        # Starting config manager (get config every 30 seconds).
        self.config_mgr = ConfigManager(self.config)
        self.config_mgr.start()

        # Starting tasks manager (launch tasks every 60 seconds).
        self.tasks_mgr = TasksManager(self.config, self.pids)
        self.tasks_mgr.start()

        # Save pids
        self.pids = {
            self.pid: 'rs_manager',
            self.pid + 1: 'rs_manager1',
            self.pid + 5: 'rs_manager5',
            self.config_mgr.pid: 'rs_config',
            self.tasks_mgr.pid: 'rs_scheduler'
        }

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Launching serverseveral times with too small delay between executions,
        # could lead to the error 'socket.error: [Errno 98] Address already in
        # use'. This is because the previous execution has left the socket in a
        # TIME_WAIT state, and can’t be immediately reused. Next line prevent
        # this behaviour.
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('127.0.0.1', 9999))
        self.socket.listen(1)

        while True:
            conn, addr = self.socket.accept()
            data = conn.recv(1024).split()
            command = data[0]
            params = data[1:]
            print("command requested: %s" % command)
            try:
                {
#                    'stop': lambda conn, params: self.stop(conn, params),
#                    'status': lambda conn, params: self.status(conn, params),
                    'stop': lambda: conn.sendall(str(self.pids)),
                    'status': lambda: conn.sendall(str({'pids': self.pids, 'config': self.config}))
                }.get(command)()
            except KeyError:
                conn.sendall("invalid command '%s'" % command)
            conn.close()


class RSDaemon(object):
    def __init__(self):
        pass


    def start(self):
        manager = ManagerServer()
        manager.start()

        # That kill current process but not the childs process.
        os.kill(os.getpid(), signal.SIGKILL)


    def stop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('127.0.0.1', 9999))
        sock.sendall('stop all')
        pids = sock.recv(1024)
        for pid, name in reversed(sorted(eval(pids).iteritems())):
            print "stopping process '%s' (%d)" % (name, pid)
            os.kill(pid, signal.SIGKILL)



    def restart(self):
        self.stop()
        self.start()


    def status(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('127.0.0.1', 9999))
        sock.send('status')
        config = sock.recv(1024)
        print eval(config)



def main():
    if len(sys.argv) != 2:
        print(USAGE)
        sys.exit(1)

    action = sys.argv[1]
    daemon = RSDaemon()

    try:
        {
            'start': lambda: daemon.start(),
            'stop': lambda: daemon.stop(),
            'restart': lambda: daemon.restart(),
            'status': lambda: daemon.status(),
            'reload': lambda: daemon.reload()
        }.get(action)()
    except KeyError:
        print(USAGE)
        print("Invalid action '%s'!" % action)
        sys.exit(1)


if __name__ == '__main__':
    main()
