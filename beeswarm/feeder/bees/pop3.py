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

import poplib
from datetime import datetime
import logging

from beeswarm.feeder.bees.clientbase import ClientBase

logger = logging.getLogger(__name__)

class pop3(ClientBase):

    def __init__(self, sessions, options):
        """
            Initializes common values.

        :param sessions: A dict which is updated every time a new session is created.
        :param options: A dict containing all options
        """
        super(pop3, self).__init__(sessions, options)

    def do_session(self, my_ip):
        """
            Launches a new POP3 client session on the server taken from the `self.options` dict.

        :param my_ip: IP of this Feeder itself
        """

        username = self.options['username']
        password = self.options['password']
        server_host = self.options['server']
        server_port = self.options['port']

        session = self.create_session(server_host, server_port, my_ip)

        try:
            logger.debug(
                'Sending %s honeybee to %s:%s. (bee id: %s)' % ('pop3', server_host, server_port, session.id))
            conn = poplib.POP3(server_host, server_port)
            session.source_port = conn.sock.getsockname()[1]

            banner = conn.getwelcome()
            session.protocol_data['banner'] = banner
            session.did_connect = True

            conn.user(username)
            conn.pass_(password)
            #TODO: Handle failed login
            session.add_auth_attempt('plaintext', True, username=username, password=password)
            session.did_login = True
            session.timestamp = datetime.utcnow()
        # except (poplib.error_proto, h_socket.error) as err:
        except Exception as err:
            logger.debug('Caught exception: %s (%s)' % (err, str(type(err))))
        else:
            list_entries = conn.list()[1]
            for entry in list_entries:
                index, octets = entry.split(' ')
                conn.retr(index)
                conn.dele(index)
            logger.debug('Found and deleted %i messages on %s' % (len(list_entries), server_host))
            conn.quit()
            session.did_complete = True
        finally:
            session.alldone = True
