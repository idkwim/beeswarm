# Copyright (C) 2013 Johnny Vestergaard <jkv@unixcluster.dk>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import json
import os
import sys
import logging
import urllib2

import requests
import gevent
from gevent.greenlet import Greenlet
import gevent.monkey
from beeswarm.shared.models.ui_handler import FeederUIHandler

gevent.monkey.patch_all()

from beeswarm.feeder.bees import clientbase
from beeswarm.feeder.models.session import BeeSession
from beeswarm.feeder.models.dispatcher import BeeDispatcher
from beeswarm.shared.asciify import asciify
from beeswarm.shared.helpers import drop_privileges
from beeswarm.feeder.consumer import consumer

# Do not remove this import, it is used to autodetect the bees.
import beeswarm.feeder.bees

logger = logging.getLogger(__name__)


class Feeder(object):
    def __init__(self, work_dir, config, curses_screen=None):

        """
            Main class which runs Beeswarm in Feeder mode.

        :param work_dir: Working directory (usually the current working directory)
        :param config_arg: Beeswarm configuration dictionary.
        :param curses_screen: Contains a curses screen object, if UI is enabled. Default is None.
        """
        self.run_flag = True
        self.curses_screen = curses_screen

        with open('beeswarmcfg.json', 'r') as config_file:
            self.config = json.load(config_file, object_hook=asciify)

        BeeSession.feeder_id = self.config['general']['feeder_id']
        BeeSession.hive_id = self.config['general']['hive_id']

        if self.config['public_ip']['fetch_ip']:
            self.my_ip = urllib2.urlopen('http://api-sth01.exip.org/?call=ip').read()
            logger.info('Fetched {0} as my external ip.'.format(self.my_ip))
        else:
            self.my_ip = '127.0.0.1'

        self.status = {
            'mode': 'Feeder',
            'total_bees': 0,
            'active_bees': 0,
            'enabled_bees': [],
            'feeder_id': self.config['general']['feeder_id'],
            'beekeeper_url': self.config['log_beekeeper']['beekeeper_url'],
            'ip_address': self.my_ip
        }

        self.dispatchers = {}
        self.dispatcher_greenlets = []

        if self.curses_screen is not None:
            self.uihandler = FeederUIHandler(self.status, self.curses_screen)
            Greenlet.spawn(self.show_status_ui)

    def show_status_ui(self):
        self.uihandler.run()

    def start(self):
        """
            Starts sending client bees to the configured Hive.
        """
        logger.info('Starting feeder.')

        sessions = {}

        #greenlet to consume and maintain data in sessions list
        self.sessions_consumer = consumer.Consumer(sessions, self.config, self.status)
        gevent.spawn(self.sessions_consumer.start_handling)

        honeybees = []
        for b in clientbase.ClientBase.__subclasses__():
            bee_name = b.__name__

            if bee_name not in self.config['honeybees']:
                logger.warning(
                    "Not loading {0} bee because it has no option in configuration file.".format(b.__name__))
                continue
                #skip loading if disabled
            if not self.config['honeybees'][bee_name]['enabled']:
                logger.warning(
                    "Not loading {0} bee because it is disabled in the configuration file.".format(b.__name__))
                continue

            options = self.config['honeybees'][bee_name]
            bee = b(sessions, options)
            honeybees.append(bee)
            self.status['enabled_bees'].append(bee_name)
            logger.debug('Adding {0} as a honeybee'.format(bee.__class__.__name__))

        self.dispatcher_greenlets = []
        for bee in honeybees:
            dispatcher = BeeDispatcher(self.config, bee, self.my_ip)
            self.dispatchers[bee.__class__.__name__] = dispatcher
            current_greenlet = Greenlet(dispatcher.start)
            self.dispatcher_greenlets.append(current_greenlet)
            current_greenlet.start()

        drop_privileges()
        gevent.joinall(self.dispatcher_greenlets)

    def stop(self):
        """
            Stop sending bees.
        """
        for g in self.dispatcher_greenlets:
            g.kill()
        if self.curses_screen is not None:
            self.uihandler.stop()
        self.sessions_consumer.stop_handling()
        logger.info('All clients stopped')
        sys.exit(0)
