from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.module_utils.common.validation import check_type_dict

from .base import BaseObjectHandler


class ARecordHandler(BaseObjectHandler):
    """Handler for record:a objects.

    Handles multiple A records with same name/different IPs,
    old_ipv4addr/new_ipv4addr updates, and nios_next_ip.
    """

    def _resolve_multiple_refs(self, ib_obj_ref, obj_filter, proposed_object):
        """Find A record matching by ipv4addr."""
        for each in ib_obj_ref:
            if each.get('ipv4addr') and proposed_object and \
               each.get('ipv4addr') == proposed_object.get('ipv4addr'):
                return each
        return obj_filter

    def post_prepare(self, proposed_object, current_object, ib_obj_type):
        """Handle new_ipv4addr field."""

        if 'ipv4addr' in proposed_object:
            if isinstance(proposed_object['ipv4addr'], str) and 'new_ipv4addr' in proposed_object['ipv4addr']:
                new_ipv4 = check_type_dict(proposed_object['ipv4addr'])['new_ipv4addr']
                proposed_object['ipv4addr'] = new_ipv4

        return proposed_object

    def check_if_nios_next_ip_exists(self, wapi, proposed_object):
        """Format ipv4addr for next_available_ip allocation."""
        from ..connector import NIOS_NEXT_AVAILABLE_IP

        if 'ipv4addr' in proposed_object:
            if isinstance(proposed_object['ipv4addr'], str) and 'nios_next_ip' in proposed_object['ipv4addr']:
                ip_range = check_type_dict(proposed_object['ipv4addr'])['nios_next_ip']
                net_view = self._get_network_view(wapi, proposed_object)
                proposed_object['ipv4addr'] = NIOS_NEXT_AVAILABLE_IP + ':' + ip_range + ',' + net_view

        return proposed_object

    def _get_network_view(self, wapi, proposed_object):
        """Get the network view associated with the dns view."""
        try:
            network_view_ref = wapi.get_object('view', {"name": proposed_object['view']},
                                               return_fields=['network_view'])
            if network_view_ref:
                return network_view_ref[0].get('network_view')
        except Exception:
            raise Exception("object with dns_view: %s not found" % proposed_object.get('view'))

    def pre_update(self, wapi, ref, proposed_object, current_object, ib_spec, module, ib_obj_type):
        """Pop 'view' before update (not supported for A records)."""
        proposed_object = self.on_update(proposed_object, ib_spec)
        proposed_object.pop('view', None)
        return ref, proposed_object

    def get_object_ref(self, wapi, module, ib_obj_type, obj_filter, ib_spec):
        """Custom lookup handling multiple A records with same name."""

        update = False
        new_name = None
        old_ipv4addr_exists = False
        next_ip_exists = False
        return_fields = list(ib_spec.keys())

        if 'name' in obj_filter:
            # Check for rename
            try:
                name_obj = check_type_dict(obj_filter['name'])
                old_name = name_obj['old_name'].lower()
                new_name = name_obj['new_name'].lower()
            except TypeError:
                old_name = None
                new_name = None

            if old_name and new_name:
                test_obj_filter = dict([('name', old_name), ('ipv4addr', obj_filter['ipv4addr'])])
                try:
                    ipaddr_obj = check_type_dict(obj_filter['ipv4addr'])
                    ipaddr = ipaddr_obj.get('old_ipv4addr')
                    old_ipv4addr_exists = True if ipaddr else False
                except TypeError:
                    ipaddr = test_obj_filter['ipv4addr']
                if old_ipv4addr_exists:
                    test_obj_filter['ipv4addr'] = ipaddr
                else:
                    del test_obj_filter['ipv4addr']

                ib_obj = wapi.get_object('record:a', test_obj_filter, return_fields=return_fields)
                if ib_obj:
                    obj_filter['name'] = new_name
                elif old_ipv4addr_exists and len(ib_obj) == 0:
                    raise Exception(
                        "object with name: '%s', ipv4addr: '%s' is not found" % (old_name, test_obj_filter.get('ipv4addr')))
                else:
                    raise Exception("object with name: '%s' is not found" % old_name)
                update = True
                return ib_obj, update, new_name

            # Normal lookup
            test_obj_filter = obj_filter.copy()
            test_obj_filter['name'] = test_obj_filter['name'].lower()

            try:
                ipaddr_obj = check_type_dict(obj_filter['ipv4addr'])
                ipaddr = ipaddr_obj.get('old_ipv4addr')
                old_ipv4addr_exists = True if ipaddr else False
                if not old_ipv4addr_exists:
                    next_ip_exists = self._check_next_ip_status(test_obj_filter)
            except TypeError:
                ipaddr = obj_filter['ipv4addr']

            if old_ipv4addr_exists:
                test_obj_filter['ipv4addr'] = ipaddr
            if next_ip_exists:
                del test_obj_filter['ipv4addr']

            ib_obj = wapi.get_object('record:a', test_obj_filter.copy(), return_fields=return_fields)

            if old_ipv4addr_exists and (ib_obj is None or len(ib_obj) == 0):
                raise Exception("A Record with ipv4addr: '%s' is not found" % ipaddr)

        else:
            # No name in filter
            test_obj_filter = obj_filter.copy()
            try:
                ipaddr_obj = check_type_dict(obj_filter['ipv4addr'])
                ipaddr = ipaddr_obj.get('old_ipv4addr')
                old_ipv4addr_exists = True if ipaddr else False
            except TypeError:
                ipaddr = obj_filter['ipv4addr']
            test_obj_filter['ipv4addr'] = ipaddr

            ib_obj = wapi.get_object('record:a', test_obj_filter.copy(), return_fields=return_fields)
            if old_ipv4addr_exists and ib_obj is None:
                raise Exception("A Record with ipv4addr: '%s' is not found" % ipaddr)

        return ib_obj, update, new_name

    def _check_next_ip_status(self, obj_filter):
        """Check if nios_next_ip exists in the filter."""
        if 'ipv4addr' in obj_filter:
            if isinstance(obj_filter['ipv4addr'], str) and 'nios_next_ip' in obj_filter['ipv4addr']:
                return True
        return False
