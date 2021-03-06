import json
import os
import uuid
import unittest
from datetime import datetime
import shutil
import gevent

from beeswarm.beekeeper.webapp.auth import Authenticator

from beeswarm.beekeeper.db import database
from beeswarm.beekeeper.db.entities import Feeder, Hive, Session, Honeybee, User, Authentication, Transcript
from beeswarm.beekeeper.webapp import app



class WebappTests(unittest.TestCase):
    def setUp(self):
        app.app.config['WTF_CSRF_ENABLED'] = False
        app.app.config['CERT_PATH'] = os.path.join(os.path.dirname(__file__), 'beeswarmcfg.json.test')
        app.app.config['BEEKEEPER_CONFIG'] = os.path.join(os.path.dirname(__file__), 'beeswarmcfg.json.test')

        self.app = app.app.test_client()
        self.authenticator = Authenticator()

        database.setup_db('sqlite://')
        session = database.get_session()

        #dummy entities
        self.authenticator.add_user('test', 'test', 0)

        self.feeder_id = str(uuid.uuid4())
        self.feeder_password = str(uuid.uuid4())
        self.authenticator.add_user(self.feeder_id, self.feeder_password, 2)

        self.hive_id = str(uuid.uuid4())
        self.hive_password = str(uuid.uuid4())
        self.authenticator.add_user(self.hive_id, self.hive_password, 1)

        session.add_all([ Feeder(id=self.feeder_id, configuration='test_feeder_config'),
                          Hive(id=self.hive_id, configuration='test_hive_config')
                        ])

        session.commit()

    def tearDown(self):
        database.clear_db()

    def test_basic_feeder_post(self):
        """
        Tests if a honeybee dict can be posted without exceptions.
        """

        self.login(self.feeder_id, self.feeder_password)

        data_dict = {
            'id': str(uuid.uuid4()),
            'feeder_id': self.feeder_id,
            'hive_id': self.hive_id,
            'protocol': 'pop3',
            'destination_ip': '127.0.0.1',
            'destination_port': '110',
            'source_ip': '123.123.123.123',
            'source_port': 12345,
            'timestamp': datetime.utcnow().isoformat(),
            'did_connect': True,
            'did_login': True,
            'did_complete': True,
            'protocol_data': None,
            'login_attempts': [{'id': str(uuid.uuid4()), 'username': 'james', 'password': 'bond', 'successful': True,
                                'timestamp': datetime.utcnow().isoformat()}]
        }

        r = self.app.post('/ws/feeder_data', data=json.dumps(data_dict), content_type='application/json')
        self.assertEquals(r.status, '200 OK')

    def test_basic_unsuccessful_feeder_post(self):
        """
        Tests if an error is returned when data is posted without ID values.
        """

        self.login(self.feeder_id, self.feeder_password)

        #missing id's
        data_dict = {
            'protocol': 'pop3',
            'username': 'james',
            'password': 'bond',
            'server_host': '127.0.0.1',
            'server_port': '110',
            'source_ip': '123.123.123.123',
            'source_port': 12345,
            'timestamp': datetime.utcnow().isoformat(),
            'did_connect': True,
            'did_login': True,
            'did_complete': True,
            'protocol_data': None
        }

        r = self.app.post('/ws/feeder_data', data=json.dumps(data_dict), content_type='application/json')
        self.assertEquals(r.status, '500 INTERNAL SERVER ERROR')

    def test_basic_hive_post(self):
        """
        Tests if a session dict can be posted without exceptions.
        """

        self.login(self.hive_id, self.hive_password)

        data_dict = {
            'id': 'ba9fdb3d-0efb-4764-9a6b-d9b86eccda96',
            'hive_id': self.hive_id,
            'destination_ip': '192.168.1.1',
            'destination_port': 8023,
            'protocol': 'telnet',
            'source_ip': '127.0.0.1',
            'timestamp': '2013-05-07T22:21:19.453828',
            'source_port': 61175,
            'login_attempts': [
                {'username': 'qqq', 'timestamp': '2013-05-07T22:21:20.846805', 'password': 'aa',
                 'id': '027bd968-f8ea-4a69-8d4c-6cf21476ca10', 'successful': False},
                {'username': 'as', 'timestamp': '2013-05-07T22:21:21.150571', 'password': 'd',
                 'id': '603f40a4-e7eb-442d-9fde-0cd3ba707af7', 'successful': False}, ],
            'transcript': [
                {'timestamp': '2013-05-07T22:21:20.846805', 'direction': 'in', 'data': 'whoami\r\n'},
                {'timestamp': '2013-05-07T22:21:21.136800', 'direction': 'out', 'data': 'james_brown\r\n$:~'}]
        }

        r = self.app.post('/ws/hive_data', data=json.dumps(data_dict), content_type='application/json')
        self.assertEquals(r.status, '200 OK')

    def test_basic_unsuccessful_hive_post(self):
        """
        Tests if an error is returned when data is posted without ID values.
        """

        self.login(self.hive_id, self.hive_password)

        #missing id
        data_dict = {
            'hive_id': self.hive_id,
            'destination_ip': '192.168.1.1',
            'destination_port': 8023,
            'protocol': 'telnet',
            'source_ip': '127.0.0.1',
            'timestamp': '2013-05-07T22:21:19.453828',
            'source_port': 61175,
            'login_attempts': [
                {'username': 'qqq', 'timestamp': '2013-05-07T22:21:20.846805', 'password': 'aa',
                 'id': '027bd968-f8ea-4a69-8d4c-6cf21476ca10', 'successful': False},
                {'username': 'as', 'timestamp': '2013-05-07T22:21:21.150571', 'password': 'd',
                 'id': '603f40a4-e7eb-442d-9fde-0cd3ba707af7', 'successful': False}, ],
            'transcript': [
                {'timestamp': '2013-05-07T22:21:20.846805', 'direction': 'in', 'data': 'whoami\r\n'},
                {'timestamp': '2013-05-07T22:21:21.136800', 'direction': 'out', 'data': 'james_brown\r\n$:~'}
            ]
        }
        r = self.app.post('/ws/hive_data', data=json.dumps(data_dict), content_type='application/json')
        self.assertEquals(r.status, '500 INTERNAL SERVER ERROR')

    def test_new_feeder(self):
        """
        Tests if a new Feeder configuration can be posted successfully
        """

        post_data = {
            'http_enabled': True,
            'http_server': '127.0.0.1',
            'http_port': 80,
            'http_active_range': '13:40 - 16:30',
            'http_sleep_interval': 0,
            'http_activation_probability': 1,
            'http_login': 'test',
            'http_password': 'test',

            'https_enabled': True,
            'https_server': '127.0.0.1',
            'https_port': 80,
            'https_active_range': '13:40 - 16:30',
            'https_sleep_interval': 0,
            'https_activation_probability': 1,
            'https_login': 'test',
            'https_password': 'test',

            'pop3s_enabled': True,
            'pop3s_server': '127.0.0.1',
            'pop3s_port': 80,
            'pop3s_active_range': '13:40 - 16:30',
            'pop3s_sleep_interval': 0,
            'pop3s_activation_probability': 1,
            'pop3s_login': 'test',
            'pop3s_password': 'test',

            'ssh_enabled': True,
            'ssh_server': '127.0.0.1',
            'ssh_port': 80,
            'ssh_active_range': '13:40 - 16:30',
            'ssh_sleep_interval': 0,
            'ssh_activation_probability': 1,
            'ssh_login': 'test',
            'ssh_password': 'test',

            'ftp_enabled': True,
            'ftp_server': '127.0.0.1',
            'ftp_port': 80,
            'ftp_active_range': '13:40 - 16:30',
            'ftp_sleep_interval': 0,
            'ftp_activation_probability': 1,
            'ftp_login': 'test',
            'ftp_password': 'test',

            'pop3_enabled': True,
            'pop3_server': '127.0.0.1',
            'pop3_port': 110,
            'pop3_active_range': '13:40 - 16:30',
            'pop3_sleep_interval': 0,
            'pop3_activation_probability': 1,
            'pop3_login': 'test',
            'pop3_password': 'test',

            'smtp_enabled': True,
            'smtp_server': '127.0.0.1',
            'smtp_port': 25,
            'smtp_active_range': '13:40 - 16:30',
            'smtp_sleep_interval': 0,
            'smtp_activation_probability': 1,
            'smtp_login': 'test',
            'smtp_password': 'test',

            'vnc_enabled': True,
            'vnc_server': '127.0.0.1',
            'vnc_port': 5900,
            'vnc_active_range': '13:40 - 16:30',
            'vnc_sleep_interval': 0,
            'vnc_activation_probability': 1,
            'vnc_login': 'test',
            'vnc_password': 'test',

            'telnet_enabled': True,
            'telnet_server': '127.0.0.1',
            'telnet_port': 23,
            'telnet_active_range': '13:40 - 16:30',
            'telnet_sleep_interval': 0,
            'telnet_activation_probability': 1,
            'telnet_login': 'test',
            'telnet_password': 'test',
        }
        self.login('test', 'test')
        resp = self.app.post('/ws/feeder', data=post_data)
        self.assertTrue(200, resp.status_code)
        self.logout()

    def test_new_hive(self):
        """
        Tests whether new Hive configuration can be posted successfully.
        """
        post_data = {
            'http_enabled': True,
            'http_port': 80,
            'http_banner': 'Microsoft-IIS/5.0',

            'https_enabled': False,
            'https_port': 443,
            'https_banner': 'Microsoft-IIS/5.0',

            'ftp_enabled': False,
            'ftp_port': 21,
            'ftp_max_attempts': 3,
            'ftp_banner': 'Microsoft FTP Server',

            'smtp_enabled': False,
            'smtp_port': 25,
            'smtp_banner': 'Microsoft ESMTP MAIL service ready',

            'vnc_enabled': False,
            'vnc_port': 5900,

            'telnet_enabled': False,
            'telnet_port': 23,
            'telnet_max_attempts': 3,

            'pop3_enabled': False,
            'pop3_port': 110,
            'pop3_max_attempts': 3,

            'pop3s_enabled': False,
            'pop3s_port': 110,
            'pop3s_max_attempts': 3,

            'ssh_enabled': False,
            'ssh_port': 22,
            'ssh_key': 'server.key'
        }
        self.login('test', 'test')
        resp = self.app.post('/ws/hive', data=post_data)
        self.assertTrue(200, resp.status_code)
        self.logout()

    def test_new_hive_config(self):
        """ Tests if a Hive config is being returned correctly """

        resp = self.app.get('/ws/hive/config/' + self.hive_id)
        self.assertEquals(resp.data, 'test_hive_config')

    def test_new_feeder_config(self):
        """ Tests if a Feeder config is being returned correctly """

        resp = self.app.get('/ws/feeder/config/' + self.feeder_id)
        self.assertEquals(resp.data, 'test_feeder_config')

    def test_data_sessions_all(self):
        """ Tests if all sessions are returned properly"""

        self.login('test', 'test')
        self.populate_sessions()
        resp = self.app.get('/data/sessions/all')
        table_data = json.loads(resp.data)
        self.assertEquals(len(table_data), 4)
        self.logout()

    def test_data_sessions_honeybees(self):
        """ Tests if honeybees are returned properly """

        self.login('test', 'test')
        self.populate_honeybees()
        resp = self.app.get('/data/sessions/honeybees')
        table_data = json.loads(resp.data)
        self.assertEquals(len(table_data), 3)
        self.logout()

    def test_data_sessions_attacks(self):
        """ Tests if attacks are returned properly """

        self.login('test', 'test')
        self.populate_sessions()
        resp = self.app.get('/data/sessions/attacks')
        table_data = json.loads(resp.data)
        self.assertEquals(len(table_data), 4)
        self.logout()

    def test_data_hive(self):
        """ Tests if Hive information is returned properly """

        self.login('test', 'test')
        self.populate_hives()
        resp = self.app.get('/data/hives')
        table_data = json.loads(resp.data)
        self.assertEquals(len(table_data), 5)  # One is added in the setup method, and 4 in populate

    def test_data_feeder(self):
        """ Tests if Feeder information is returned properly """

        self.login('test', 'test')
        self.populate_feeders()
        resp = self.app.get('/data/feeders')
        table_data = json.loads(resp.data)
        self.assertEquals(len(table_data), 5)  # One is added in the setup method, and 4 in populate

    def test_data_transcripts(self):
        """ Tests that if given a session ID we can extract the relevant transcripts"""
        db_session = database.get_session()
        self.login('test', 'test')
        session_id = str(uuid.uuid4())

        timestamp = datetime.utcnow()

        db_session.add(Transcript(timestamp=timestamp, direction='outgoing', data='whoami', session_id=session_id))
        db_session.add(Transcript(timestamp=timestamp, direction='outgoing', data='root\r\n', session_id=session_id))
        db_session.commit()
        resp = self.app.get('/data/session/{0}/transcript'.format(session_id))
        data = json.loads(resp.data)
        string_timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        expected_result = [{u'direction': u'outgoing', u'data': u'whoami', u'time': u'{0}'.format(string_timestamp)},
                           {u'direction': u'outgoing', u'data': u'root\r\n', u'time': u'{0}'.format(string_timestamp)}]
        self.assertDictEqual(sorted(data)[0], sorted(expected_result)[0])


    def test_settings(self):
        """ Tests if new settings are successfully written to the config file """

        self.login('test', 'test')
        with open(app.app.config['BEEKEEPER_CONFIG'], 'r') as conf:
            original_config = conf.read()
        config_modified = os.stat(app.app.config['BEEKEEPER_CONFIG']).st_mtime
        data = {
            'honeybee_session_retain': 3,
            'malicious_session_retain': 50,
            'ignore_failed_honeybees': False
        }
        self.app.post('/settings', data=data, follow_redirects=True)
        config_next_modified = os.stat(app.app.config['BEEKEEPER_CONFIG']).st_mtime
        self.assertTrue(config_next_modified > config_modified)

        # Restore original configuration
        with open(app.app.config['BEEKEEPER_CONFIG'], 'w') as conf:
            conf.write(original_config)

    def test_login_logout(self):
        """ Tests basic login/logout """

        self.login('test', 'test')
        self.logout()

    def test_hive_delete(self):
        """ Tests the '/ws/hive/delete' route."""

        self.login('test', 'test')
        self.populate_hives()
        data = [
            {'attacks': 0, 'checked': False, 'hive_id': self.hives[0]},
            {'attacks': 0, 'checked': False, 'hive_id': self.hives[1]}
        ]
        self.app.post('/ws/hive/delete', data=json.dumps(data))
        db_session = database.get_session()
        nhives = db_session.query(Hive).count()
        self.assertEquals(3, nhives)

    def test_feeder_delete(self):
        """ Tests the '/ws/feeder/delete' route."""

        self.login('test', 'test')
        self.populate_feeders()
        data = [
            {'feeder_id': self.feeders[0], 'bees': 0, 'checked': False},
            {'feeder_id': self.feeders[1], 'bees': 0, 'checked': False}
        ]
        self.app.post('/ws/feeder/delete', data=json.dumps(data))
        db_session = database.get_session()
        nfeeders = db_session.query(Feeder).count()
        self.assertEquals(3, nfeeders)

    def populate_feeders(self):
        """ Populates the database with 4 Feeders """

        db_session = database.get_session()
        self.feeders = []
        for i in xrange(4):  # We add 4 here, but one is added in the setup method
            curr_id = str(uuid.uuid4())
            curr_id = curr_id.encode('utf-8')
            self.feeders.append(curr_id)
            u = User(id=curr_id, password=str(uuid.uuid4()), utype=2)
            f = Feeder(id=curr_id)
            db_session.add(f)
            db_session.add(u)
        db_session.commit()

    def populate_hives(self):
        """ Populates the database with 4 Hives """

        db_session = database.get_session()
        self.hives = []
        for i in xrange(4):  # We add 4 here, but one is added in the setup method
            curr_id = str(uuid.uuid4())
            curr_id = curr_id.encode('utf-8')
            self.hives.append(curr_id)
            h = Hive(id=curr_id)
            u = User(id=curr_id, password=str(uuid.uuid4()), utype=1)
            db_session.add(h)
            db_session.add(u)
        db_session.commit()

    def login(self, username, password):
        """ Logs into the web-app """

        data = {
            'username': username,
            'password': password
        }
        return self.app.post('/login', data=data, follow_redirects=True)

    def populate_honeybees(self):
        """ Populates the database with 3 Honeybees """

        db_session = database.get_session()
        for i in xrange(3):
            h = Honeybee(
                id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                received=datetime.utcnow(),
                protocol='ssh',
                destination_ip='1.2.3.4',
                destination_port=1234,
                source_ip='4.3.2.1',
                source_port=4321,
                did_connect=True,
                did_login=False,
                did_complete=True
            )
            a = Authentication(id=str(uuid.uuid4()), username='uuu', password='vvvv',
                               successful=False,
                               timestamp=datetime.utcnow())
            h.authentication.append(a)
            db_session.add(h)

        db_session.commit()

    def populate_sessions(self):
        """ Populates the database with 3 Sessions """

        db_session = database.get_session()
        for i in xrange(4):
            s = Session(
                id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                received=datetime.utcnow(),
                protocol='telnet',
                destination_ip='123.123.123.123',
                destination_port=1234,
                source_ip='12.12.12.12',
                source_port=12345,
                classification_id='asd'
            )
            a = Authentication(id=str(uuid.uuid4()), username='aaa', password='bbb',
                               successful=False,
                               timestamp=datetime.utcnow())
            s.authentication.append(a)
            db_session.add(s)

        db_session.commit()

    def logout(self):
        return self.app.get('/logout', follow_redirects=True)


if __name__ == '__main__':
    unittest.main()
