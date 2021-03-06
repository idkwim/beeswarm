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
# along with this program.  If not, see <http://www.gnu.org/licenses/>

from datetime import datetime, timedelta
import logging

import gevent
from gevent import Greenlet

from beeswarm.beekeeper.db import database
from beeswarm.beekeeper.db.entities import Session
from beeswarm.beekeeper.classifier.classifier import Classifier

logger = logging.getLogger(__name__)


class Scheduler(object):
    def __init__(self, config):
        self.config = config
        self.enabled = False

    def start(self):
        self.enabled = True

        #key: method name.
        #value: parameter for spawn_later (seconds).
        schedules = {'do_db_maintenance': 3600,
                     'do_classification': 10}

        #will contain running and stopped (ready()) greenlets.
        greenlets = {}

        while self.enabled:
            for function, seconds in schedules.items():
                if function not in greenlets or greenlets[function].ready():
                    greenlets[function] = Greenlet(getattr(self, function))
                    greenlets[function].start_later(schedules[function])
            gevent.sleep(1)

    def stop(self):
        self.enabled = False

    def do_db_maintenance(self):
        logger.debug('Doing database maintenance')
        honeybee_retain = datetime.utcnow() - timedelta(days=self.config['honeybee_session_retain'])
        malicious_retain = datetime.utcnow() - timedelta(days=self.config['malicious_session_retain'])

        db_session = database.get_session()

        malicious_deleted_count = db_session.query(Session).filter(Session.classification_id != 'honeybee') \
                                                           .filter(Session.timestamp < malicious_retain).delete()

        honeybees_deleted_count = db_session.query(Session).filter(Session.classification_id == 'honeybee') \
                                                           .filter(Session.timestamp < honeybee_retain).delete()
        db_session.commit()

        logger.debug('Database maintenance finished. Deleted {0} honeybees and {1} malicious sessions)' \
                     .format(honeybees_deleted_count, malicious_deleted_count))

    def do_classification(self):
        db_session = database.get_session()
        classifier = Classifier()
        classifier.classify_honeybees(db_session=db_session)
        classifier.classify_sessions(db_session=db_session)
        db_session.commit()


