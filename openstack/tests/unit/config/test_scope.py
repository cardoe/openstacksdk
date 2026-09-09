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

import openstack
from openstack.config import loader
from openstack import exceptions
from openstack.tests.unit.config import base


BASE_AUTH = {
    'auth_url': 'https://example.com/v3',
    'username': 'alice',
    'password': 'password',
    'user_domain_name': 'Default',
}
SCOPE = {
    'project_name': 'demo',
    'project_domain_name': 'Default',
    'system': 'all',
    'domain_name': 'Default',
}


class TestScope(base.TestCase):
    def setUp(self):
        super().setUp()
        self.config = loader.OpenStackConfig(
            load_yaml_config=False, load_envvars=False
        )

    def _get_one(self, scope_name=None, scope=None, auth=None):
        return self.config.get_one(
            auth=dict(auth or BASE_AUTH),
            scope=dict(SCOPE if scope is None else scope),
            region_name='RegionOne',
            scope_name=scope_name,
        )

    def _scope_attrs(self, region):
        auth = region.get_auth()
        keys = (
            'project_id',
            'project_name',
            'project_domain_id',
            'project_domain_name',
            'system_scope',
            'domain_id',
            'domain_name',
        )
        result = {}
        for key in keys:
            value = getattr(auth, key, None) or getattr(auth, f'_{key}', None)
            if value:
                result[key] = value
        return result

    def test_default_scope_is_project(self):
        region = self._get_one()
        self.assertEqual(['project', 'domain', 'system'], region.get_scopes())
        self.assertEqual(
            {'project_name': 'demo', 'project_domain_name': 'Default'},
            self._scope_attrs(region),
        )

    def test_explicit_project_scope(self):
        region = self._get_one('project')
        self.assertEqual(
            {'project_name': 'demo', 'project_domain_name': 'Default'},
            self._scope_attrs(region),
        )

    def test_system_scope(self):
        region = self._get_one('system')
        # 'system' in a scope block is an alias for 'system_scope'.
        self.assertEqual({'system_scope': 'all'}, self._scope_attrs(region))

    def test_domain_scope(self):
        region = self._get_one('domain')
        self.assertEqual({'domain_name': 'Default'}, self._scope_attrs(region))

    def test_selected_scope_replaces_leftover_scope_in_auth(self):
        # A scope target already sitting in the auth block must not leak into
        # the selected scope and produce two conflicting targets.
        auth = dict(BASE_AUTH)
        auth['project_id'] = 'leftover'
        region = self._get_one('system', auth=auth)
        self.assertEqual({'system_scope': 'all'}, self._scope_attrs(region))

    def test_default_when_only_system_present(self):
        region = self._get_one(scope={'system': 'all'})
        self.assertEqual(['system'], region.get_scopes())
        self.assertEqual({'system_scope': 'all'}, self._scope_attrs(region))

    def test_unknown_scope_raises(self):
        self.assertRaises(exceptions.ConfigException, self._get_one, 'bogus')

    def test_undefined_scope_raises(self):
        # 'domain' is not populated here, so requesting it fails.
        self.assertRaises(
            exceptions.ConfigException,
            self._get_one,
            'domain',
            {'project_name': 'demo', 'project_domain_name': 'Default'},
        )

    def test_scope_requested_without_scope_block(self):
        self.assertRaises(
            exceptions.ConfigException,
            self.config.get_one,
            auth=dict(BASE_AUTH),
            region_name='RegionOne',
            scope_name='project',
        )

    def test_no_scope_block_is_a_noop(self):
        region = self.config.get_one(
            auth=dict(BASE_AUTH, project_name='demo'),
            region_name='RegionOne',
        )
        self.assertEqual([], region.get_scopes())


class TestScopedConnection(base.TestCase):
    def setUp(self):
        super().setUp()
        self.config = loader.OpenStackConfig(
            load_yaml_config=False, load_envvars=False
        )
        region = self.config.get_one(
            auth=dict(BASE_AUTH),
            scope=dict(SCOPE),
            region_name='RegionOne',
        )
        self.conn = openstack.connection.Connection(config=region)

    def _scope_of(self, conn):
        auth = conn.config.get_auth()
        return {
            'project_name': getattr(auth, '_project_name', None),
            'system_scope': getattr(auth, '_system_scope', None),
            'domain_name': getattr(auth, '_domain_name', None),
        }

    def test_base_connection_uses_default_scope(self):
        self.assertEqual(
            ['project', 'domain', 'system'], self.conn.config.get_scopes()
        )
        self.assertEqual('demo', self._scope_of(self.conn)['project_name'])

    def test_scoped_returns_system_scoped_sibling(self):
        admin = self.conn.scoped('system')
        self.assertIsNot(admin, self.conn)
        self.assertEqual('all', self._scope_of(admin)['system_scope'])
        # The original connection is unchanged.
        self.assertEqual('demo', self._scope_of(self.conn)['project_name'])

    def test_connect_as_system(self):
        admin = self.conn.connect_as_system()
        self.assertEqual('all', self._scope_of(admin)['system_scope'])

    def test_scoped_shares_credential(self):
        admin = self.conn.scoped('system')
        self.assertEqual(
            getattr(self.conn.config.get_auth(), '_username', None),
            getattr(admin.config.get_auth(), '_username', None),
        )

    def test_scoped_unknown_scope_raises(self):
        self.assertRaises(
            exceptions.ConfigException, self.conn.scoped, 'bogus'
        )
