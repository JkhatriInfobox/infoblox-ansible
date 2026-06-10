# (c) 2018 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import copy
try:
    from ansible_collections.infoblox.nios_modules.tests.unit.compat import unittest
except ImportError:
    import unittest
from ansible_collections.infoblox.nios_modules.tests.unit.compat.mock import patch, MagicMock, Mock
from ansible_collections.infoblox.nios_modules.plugins.module_utils import api


class TestNiosApi(unittest.TestCase):

    def setUp(self):
        super(TestNiosApi, self).setUp()

        self.module = MagicMock(name='AnsibleModule')
        self.module.check_mode = False
        self.module.params = {'provider': None}

        self.mock_connector = patch('ansible_collections.infoblox.nios_modules.plugins.module_utils.api.get_connector')
        self.mock_connector.start()
        self.mock_check_type_dict = patch('ansible.module_utils.common.validation.check_type_dict')
        self.mock_check_type_dict_obj = self.mock_check_type_dict.start()

    def tearDown(self):
        super(TestNiosApi, self).tearDown()

        self.mock_connector.stop()
        self.mock_check_type_dict.stop()

    def test_get_provider_spec(self):
        provider_options = ['host', 'username', 'password', 'cert', 'key', 'validate_certs', 'silent_ssl_warnings',
                            'http_request_timeout', 'http_pool_connections',
                            'http_pool_maxsize', 'max_retries', 'wapi_version', 'max_results']
        res = api.WapiBase.provider_spec
        self.assertIsNotNone(res)
        self.assertIn('provider', res)
        self.assertIn('options', res['provider'])
        returned_options = res['provider']['options']
        self.assertEqual(sorted(provider_options), sorted(returned_options.keys()))

    def _get_wapi(self, test_object):
        wapi = api.WapiModule(self.module)
        wapi.get_object = Mock(name='get_object', return_value=test_object)
        wapi.create_object = Mock(name='create_object')
        wapi.update_object = Mock(name='update_object')
        wapi.delete_object = Mock(name='delete_object')
        return wapi

    def test_wapi_no_change(self):
        self.module.params = {'provider': None, 'state': 'present', 'name': 'default',
                              'comment': 'test comment', 'extattrs': None}

        test_object = [
            {
                "comment": "test comment",
                "_ref": "networkview/ZG5zLm5ldHdvcmtfdmlldyQw:default/true",
                "name": 'default',
                "extattrs": {}
            }
        ]

        test_spec = {
            "name": {"ib_req": True},
            "comment": {},
            "extattrs": {}
        }

        wapi = self._get_wapi(test_object)
        res = wapi.run('testobject', test_spec)

        self.assertFalse(res['changed'])

    def test_wapi_change(self):
        self.module.params = {'provider': None, 'state': 'present', 'name': 'default',
                              'comment': 'updated comment', 'extattrs': None}
        ref = "networkview/ZG5zLm5ldHdvcmtfdmlldyQw:default/true"
        test_object = [
            {
                "comment": "test comment",
                "_ref": ref,
                "name": "default",
                "extattrs": {}
            }
        ]

        test_spec = {
            "name": {"ib_req": True},
            "comment": {},
            "extattrs": {}
        }

        wapi = self._get_wapi(test_object)
        res = wapi.run('testobject', test_spec)

        self.assertTrue(res['changed'])
        wapi.update_object.assert_called_once_with(ref, {'comment': 'updated comment', 'name': 'default'})

    def test_wapi_change_false(self):
        self.module.params = {'provider': None, 'state': 'present', 'name': 'default',
                              'comment': 'updated comment', 'extattrs': None, 'fqdn': 'foo'}
        ref = "networkview/ZG5zLm5ldHdvcmtfdmlldyQw:default/true"
        test_object = [
            {
                "comment": "test comment",
                "_ref": ref,
                "name": "default",
                "extattrs": {}
            }
        ]

        test_spec = {
            "name": {"ib_req": True},
            "fqdn": {"ib_req": True, 'update': False},
            "comment": {},
            "extattrs": {}
        }

        wapi = self._get_wapi(test_object)
        res = wapi.run('testobject', test_spec)

        self.assertTrue(res['changed'])
        wapi.update_object.assert_called_once_with(
            ref, {'comment': 'updated comment', 'name': 'default'}
        )

    def test_wapi_extattrs_change(self):
        self.module.params = {'provider': None, 'state': 'present', 'name': 'default',
                              'comment': 'test comment', 'extattrs': {'Site': 'update'}}

        ref = "networkview/ZG5zLm5ldHdvcmtfdmlldyQw:default/true"

        test_object = [{
            "comment": "test comment",
            "_ref": ref,
            "name": "default",
            "extattrs": {'Site': {'value': 'test'}}
        }]

        test_spec = {
            "name": {"ib_req": True},
            "comment": {},
            "extattrs": {}
        }

        kwargs = copy.deepcopy(test_object[0])
        kwargs['extattrs']['Site']['value'] = 'update'
        kwargs['name'] = 'default'
        del kwargs['_ref']

        wapi = self._get_wapi(test_object)
        res = wapi.run('testobject', test_spec)

        self.assertTrue(res['changed'])
        wapi.update_object.assert_called_once_with(ref, kwargs)

    def test_wapi_extattrs_nochange(self):
        self.module.params = {'provider': None, 'state': 'present', 'name': 'default',
                              'comment': 'test comment', 'extattrs': {'Site': 'test'}}

        ref = "networkview/ZG5zLm5ldHdvcmtfdmlldyQw:default/true"
        test_object = [{
            "comment": "test comment",
            "_ref": ref,
            "name": "default",
            "extattrs": {'Site': {'value': 'test'}}
        }]

        test_spec = {
            "name": {"ib_req": True},
            "comment": {},
            "extattrs": {}
        }

        wapi = self._get_wapi(test_object)
        res = wapi.run('testobject', test_spec)

        self.assertFalse(res['changed'])
        wapi.update_object.assert_not_called()

    def test_wapi_create(self):
        self.module.params = {'provider': None, 'state': 'present', 'name': 'ansible',
                              'comment': None, 'extattrs': None}

        test_object = None

        test_spec = {
            "name": {"ib_req": True},
            "comment": {},
            "extattrs": {}
        }

        wapi = self._get_wapi(test_object)
        res = wapi.run('testobject', test_spec)

        self.assertTrue(res['changed'])
        wapi.create_object.assert_called_once_with('testobject', {'name': 'ansible'})

    def test_wapi_delete(self):
        self.module.params = {'provider': None, 'state': 'absent', 'name': 'ansible',
                              'comment': None, 'extattrs': None}

        ref = "networkview/ZG5zLm5ldHdvcmtfdmlldyQw:ansible/false"

        test_object = [{
            "comment": "test comment",
            "_ref": ref,
            "name": "ansible",
            "extattrs": {'Site': {'value': 'test'}}
        }]

        test_spec = {
            "name": {"ib_req": True},
            "comment": {},
            "extattrs": {}
        }

        wapi = self._get_wapi(test_object)
        res = wapi.run('testobject', test_spec)

        self.assertTrue(res['changed'])
        wapi.delete_object.assert_called_once_with(ref)

    def test_wapi_strip_network_view(self):
        self.module.params = {'provider': None, 'state': 'present', 'name': 'ansible',
                              'comment': 'updated comment', 'extattrs': None,
                              'network_view': 'default'}

        test_object = [{
            "comment": "test comment",
            "_ref": "view/ZG5zLm5ldHdvcmtfdmlldyQw:ansible/true",
            "name": "ansible",
            "extattrs": {},
            "network_view": "default"
        }]

        test_spec = {
            "name": {"ib_req": True},
            "network_view": {"ib_req": True},
            "comment": {},
            "extattrs": {}
        }

        kwargs = test_object[0].copy()
        ref = kwargs.pop('_ref')
        kwargs['comment'] = 'updated comment'
        kwargs['name'] = 'ansible'
        del kwargs['network_view']
        del kwargs['extattrs']

        wapi = self._get_wapi(test_object)
        res = wapi.run('testobject', test_spec)

        self.assertTrue(res['changed'])
        wapi.update_object.assert_called_once_with(ref, kwargs)

    # ------------------------------------------------------------------
    # Issue #300: IPAM-only (non-DNS) host records carry view=' ' in WAPI.
    # The tests below cover the new view-handling paths in WapiModule.run()
    # and WapiModule.get_object_ref().
    # ------------------------------------------------------------------

    @staticmethod
    def _host_record_spec():
        return {
            "name": {"ib_req": True},
            "view": {"ib_req": True},
            "configure_for_dns": {"ib_req": True},
            "ipv4addrs": {},
            "comment": {},
            "extattrs": {},
        }

    def test_host_record_blank_view_omits_view_from_lookup(self):
        # User explicitly passes view=' ' (an IPAM-only host record's WAPI
        # marker). The lookup must be performed without 'view' in the
        # search filter so WAPI doesn't return 'View not found'.
        ref = "record:host/ZG5zLmhvc3QkLl9kZWZhdWx0Lmlwc28x:ipso-host/%20"
        ipam_only = {
            "_ref": ref, "name": "ipso-host", "view": " ",
            "configure_for_dns": False, "ipv4addrs": [], "extattrs": {},
        }
        self.module.params = {
            'provider': None, 'state': 'absent', 'name': 'ipso-host',
            'view': ' ', 'configure_for_dns': False,
            'ipv4addrs': None, 'comment': None, 'extattrs': None,
        }
        wapi = self._get_wapi([ipam_only])
        res = wapi.run(api.NIOS_HOST_RECORD, self._host_record_spec())

        self.assertTrue(res['changed'])
        wapi.delete_object.assert_called_once_with(ref)
        # The lookup filter passed to get_object must not contain 'view'
        # when the user-supplied view is blank/whitespace.
        called_filter = wapi.get_object.call_args[0][1]
        self.assertNotIn('view', called_filter)

    def test_host_record_default_view_retry_finds_ipam_only(self):
        # User runs state=absent without specifying view, so view defaults
        # to 'default'. The first lookup (view='default') returns nothing;
        # the retry without the view filter must find the IPAM-only record
        # (view=' ') and delete it.
        ref = "record:host/ZG5zLmhvc3QkLl9kZWZhdWx0Lmlwc28x:ipso-host/%20"
        ipam_only = {
            "_ref": ref, "name": "ipso-host", "view": " ",
            "configure_for_dns": False, "ipv4addrs": [], "extattrs": {},
        }
        responses = [[], [ipam_only]]
        self.module.params = {
            'provider': None, 'state': 'absent', 'name': 'ipso-host',
            'view': 'default', 'configure_for_dns': True,
            'ipv4addrs': None, 'comment': None, 'extattrs': None,
        }
        wapi = api.WapiModule(self.module)
        wapi.get_object = Mock(side_effect=responses)
        wapi.create_object = Mock()
        wapi.update_object = Mock()
        wapi.delete_object = Mock()

        res = wapi.run(api.NIOS_HOST_RECORD, self._host_record_spec())

        self.assertTrue(res['changed'])
        wapi.delete_object.assert_called_once_with(ref)

    def test_host_record_default_view_retry_ignores_other_dns_views(self):
        # The retry path must NOT match records that live in a non-default
        # DNS view (view='external'); those are not IPAM-only records and
        # acting on them would be wrong. The module should treat the
        # absent operation as a no-op (changed=False).
        external_view_record = {
            "_ref": "record:host/abc:ipso-host/external",
            "name": "ipso-host", "view": "external",
            "configure_for_dns": True, "ipv4addrs": [], "extattrs": {},
        }
        responses = [[], [external_view_record]]
        self.module.params = {
            'provider': None, 'state': 'absent', 'name': 'ipso-host',
            'view': 'default', 'configure_for_dns': True,
            'ipv4addrs': None, 'comment': None, 'extattrs': None,
        }
        wapi = api.WapiModule(self.module)
        wapi.get_object = Mock(side_effect=responses)
        wapi.create_object = Mock()
        wapi.update_object = Mock()
        wapi.delete_object = Mock()

        res = wapi.run(api.NIOS_HOST_RECORD, self._host_record_spec())

        self.assertFalse(res['changed'])
        wapi.delete_object.assert_not_called()

    def test_host_record_blank_view_multiple_matches_fails(self):
        # If the IPAM-only name-only fallback search returns more than one
        # eligible (blank-view) record, the module must fail rather than
        # silently picking one.
        match_a = {
            "_ref": "record:host/a:ipso-host/%20",
            "name": "ipso-host", "view": " ",
            "configure_for_dns": False, "ipv4addrs": [], "extattrs": {},
        }
        match_b = {
            "_ref": "record:host/b:ipso-host/%20",
            "name": "ipso-host", "view": " ",
            "configure_for_dns": False, "ipv4addrs": [], "extattrs": {},
        }
        self.module.params = {
            'provider': None, 'state': 'absent', 'name': 'ipso-host',
            'view': ' ', 'configure_for_dns': False,
            'ipv4addrs': None, 'comment': None, 'extattrs': None,
        }
        wapi = self._get_wapi([match_a, match_b])
        self.module.fail_json.reset_mock()
        self.module.fail_json.side_effect = SystemExit(1)

        with self.assertRaises(SystemExit):
            wapi.run(api.NIOS_HOST_RECORD, self._host_record_spec())

        self.module.fail_json.assert_called_once()
        msg_kwargs = self.module.fail_json.call_args[1]
        self.assertIn('multiple IPAM-only host records', msg_kwargs.get('msg', ''))
        wapi.delete_object.assert_not_called()

    def test_host_record_configure_for_dns_false_filters_out_dns_records(self):
        # Legacy fallback: when configure_for_dns=False, the lookup falls
        # back to name-only even if view='default'. If a DNS-enabled host
        # with the same name exists in some view, name-only search returns
        # both. The module must filter out the DNS-enabled record and act
        # only on the IPAM-only one (configure_for_dns=False).
        ipam_only_ref = "record:host/a:ipso-host/%20"
        dns_record = {
            "_ref": "record:host/b:ipso-host/default",
            "name": "ipso-host", "view": "default",
            "configure_for_dns": True, "ipv4addrs": [], "extattrs": {},
        }
        ipam_only = {
            "_ref": ipam_only_ref, "name": "ipso-host", "view": " ",
            "configure_for_dns": False, "ipv4addrs": [], "extattrs": {},
        }
        self.module.params = {
            'provider': None, 'state': 'absent', 'name': 'ipso-host',
            'view': 'default', 'configure_for_dns': False,
            'ipv4addrs': None, 'comment': None, 'extattrs': None,
        }
        wapi = self._get_wapi([dns_record, ipam_only])

        res = wapi.run(api.NIOS_HOST_RECORD, self._host_record_spec())

        self.assertTrue(res['changed'])
        wapi.delete_object.assert_called_once_with(ipam_only_ref)

    def test_post_fetch_filters_password_for_adminuser(self):
        # Post-write re-fetch should never request password in return_fields
        # because WAPI rejects adminuser GETs with return_fields+=password.
        self.module.params = {
            'provider': {}, 'state': 'present',
            'name': 'api-user', 'password': 'secret',
        }
        test_spec = {
            'name': {'ib_req': True},
            'password': {},
        }

        wapi = api.WapiModule(self.module)
        wapi.get_object = Mock(return_value=None)
        wapi.create_object = Mock(return_value='adminuser/test-ref')
        wapi.update_object = Mock()
        wapi.delete_object = Mock()
        wapi.connector.get_object = Mock(return_value={'_ref': 'adminuser/test-ref', 'name': 'api-user'})

        res = wapi.run(api.NIOS_ADMINUSER, test_spec)

        self.assertTrue(res['changed'])
        self.assertIn('object', res)
        called_kwargs = wapi.connector.get_object.call_args.kwargs
        self.assertIn('return_fields', called_kwargs)
        self.assertNotIn('password', called_kwargs['return_fields'])

    def test_post_fetch_result_object_populated_on_create(self):
        self.module.params = {"provider": {}, "state": "present", "name": "new-host", "comment": None}
        test_spec = {"name": {"ib_req": True}, "comment": {}}
        wapi = api.WapiModule(self.module)
        wapi.get_object = Mock(return_value=None)
        wapi.create_object = Mock(return_value="record:a/abc123")
        wapi.update_object = Mock()
        wapi.delete_object = Mock()
        wapi.connector.get_object = Mock(return_value={"_ref": "record:a/abc123", "name": "new-host"})
        res = wapi.run("testobject", test_spec)
        self.assertTrue(res["changed"])
        self.assertIn("object", res)
        self.assertEqual(res["object"]["_ref"], "record:a/abc123")

    def test_post_fetch_result_object_populated_on_update(self):
        ref = "testobject/ZG5z:existing/default"
        self.module.params = {"provider": {}, "state": "present", "name": "host", "comment": "updated"}
        test_object = [{"_ref": ref, "name": "host", "comment": "old"}]
        test_spec = {"name": {"ib_req": True}, "comment": {}}
        wapi = api.WapiModule(self.module)
        wapi.get_object = Mock(return_value=test_object)
        wapi.create_object = Mock()
        wapi.update_object = Mock(return_value=ref)
        wapi.delete_object = Mock()
        wapi.connector.get_object = Mock(return_value={"_ref": ref, "comment": "updated"})
        res = wapi.run("testobject", test_spec)
        self.assertTrue(res["changed"])
        self.assertIn("object", res)
        self.assertEqual(res["object"]["comment"], "updated")

    def test_post_fetch_skipped_for_nios_member(self):
        self.module.params = {"provider": {}, "state": "present", "name": "member.grid.example.com", "create_token": False}
        test_spec = {"name": {"ib_req": True}, "create_token": {}}
        wapi = api.WapiModule(self.module)
        wapi.get_object = Mock(return_value=None)
        wapi.create_object = Mock(return_value="member/abc123")
        wapi.update_object = Mock()
        wapi.delete_object = Mock()
        wapi.connector.get_object = Mock()
        res = wapi.run(api.NIOS_MEMBER, test_spec)
        self.assertTrue(res["changed"])
        self.assertNotIn("object", res)
        wapi.connector.get_object.assert_not_called()

    def test_post_fetch_skipped_in_check_mode(self):
        self.module.check_mode = True
        self.module.params = {"provider": {}, "state": "present", "name": "dryrun", "comment": None}
        test_spec = {"name": {"ib_req": True}, "comment": {}}
        wapi = api.WapiModule(self.module)
        wapi.get_object = Mock(return_value=None)
        wapi.create_object = Mock()
        wapi.update_object = Mock()
        wapi.delete_object = Mock()
        wapi.connector.get_object = Mock()
        res = wapi.run("testobject", test_spec)
        self.assertTrue(res["changed"])
        self.assertNotIn("object", res)
        wapi.connector.get_object.assert_not_called()
        wapi.create_object.assert_not_called()

    def test_post_fetch_warns_on_connector_error(self):
        self.module.params = {"provider": {}, "state": "present", "name": "new-host", "comment": None}
        test_spec = {"name": {"ib_req": True}, "comment": {}}
        wapi = api.WapiModule(self.module)
        wapi.get_object = Mock(return_value=None)
        wapi.create_object = Mock(return_value="record:a/abc123")
        wapi.update_object = Mock()
        wapi.delete_object = Mock()
        wapi.connector.get_object = Mock(side_effect=Exception("WAPI timeout"))
        res = wapi.run("testobject", test_spec)
        self.assertTrue(res["changed"])
        self.assertNotIn("object", res)
        self.module.warn.assert_called_once()
        self.assertIn("post-write object fetch failed", self.module.warn.call_args[0][0])

    def test_post_fetch_excludes_members_and_vlans_from_return_fields(self):
        self.module.params = {"provider": {}, "state": "present", "name": "net", "members": [], "vlans": []}
        test_spec = {"name": {"ib_req": True}, "members": {}, "vlans": {}}
        wapi = api.WapiModule(self.module)
        wapi.get_object = Mock(return_value=None)
        wapi.create_object = Mock(return_value="testobject/net-ref")
        wapi.update_object = Mock()
        wapi.delete_object = Mock()
        wapi.connector.get_object = Mock(return_value={"_ref": "testobject/net-ref"})
        res = wapi.run("testobject", test_spec)
        self.assertTrue(res["changed"])
        called_kwargs = wapi.connector.get_object.call_args.kwargs
        self.assertNotIn("members", called_kwargs.get("return_fields", []))
        self.assertNotIn("vlans", called_kwargs.get("return_fields", []))
