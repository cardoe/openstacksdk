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

from typing import Any
from unittest import mock

from keystoneauth1 import adapter

from openstack.baremetal.v1 import conductor
from openstack.tests.unit import base


FAKE: dict[str, Any] = {
    "links": [
        {
            "href": "http://127.0.0.1:6385/v1/conductors/compute2.localdomain",
            "rel": "self",
        },
        {
            "href": "http://127.0.0.1:6385/conductors/compute2.localdomain",
            "rel": "bookmark",
        },
    ],
    "created_at": "2018-12-05T07:03:19+00:00",
    "hostname": "compute2.localdomain",
    "conductor_group": "",
    "updated_at": "2018-12-05T07:03:21+00:00",
    "alive": True,
    "drivers": ["ipmi"],
}


class TestContainer(base.TestCase):
    def test_basic(self):
        sot = conductor.Conductor()
        self.assertIsNone(sot.resource_key)
        self.assertEqual('conductors', sot.resources_key)
        self.assertEqual('/conductors', sot.base_path)
        self.assertFalse(sot.allow_create)
        self.assertTrue(sot.allow_fetch)
        self.assertFalse(sot.allow_commit)
        self.assertFalse(sot.allow_delete)
        self.assertTrue(sot.allow_list)
        self.assertFalse(sot.allow_patch)

    def test_instantiate(self):
        sot = conductor.Conductor(**FAKE)
        self.assertEqual(FAKE['created_at'], sot.created_at)
        self.assertEqual(FAKE['updated_at'], sot.updated_at)
        self.assertEqual(FAKE['hostname'], sot.hostname)
        self.assertEqual(FAKE['conductor_group'], sot.conductor_group)
        self.assertEqual(FAKE['alive'], sot.alive)
        self.assertEqual(FAKE['links'], sot.links)
        self.assertEqual(FAKE['drivers'], sot.drivers)


class TestConductorList(base.TestCase):
    def setUp(self):
        super().setUp()
        self.session = mock.Mock(
            spec=adapter.Adapter,
            default_microversion=conductor.Conductor._max_microversion,
        )
        self.session.get.return_value.status_code = 200
        self.session.get.return_value.json.return_value = {'conductors': []}

    def test_list(self):
        result = list(conductor.Conductor.list(self.session))
        self.assertEqual([], result)
        self.session.get.assert_called_once_with(
            '/conductors',
            headers={'Accept': 'application/json'},
            params={},
            microversion=conductor.Conductor._max_microversion,
        )

    def test_list_detail(self):
        result = list(conductor.Conductor.list(self.session, detail=True))
        self.assertEqual([], result)
        self.session.get.assert_called_once_with(
            '/conductors',
            headers={'Accept': 'application/json'},
            params={'detail': True},
            microversion=conductor.Conductor._max_microversion,
        )
