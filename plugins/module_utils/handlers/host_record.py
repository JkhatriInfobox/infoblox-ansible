from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.module_utils.common.validation import check_type_dict

import copy
from .base import BaseObjectHandler


class HostRecordHandler(BaseObjectHandler):
    """Handler for record:host objects.

    Host records are the most complex type with ipv4addrs add/remove,
    next_ip allocation, configure_for_dns bypass, and use_for_ea_inheritance.
    """

    def _resolve_multiple_refs(self, ib_obj_ref, obj_filter, proposed_object):
        """When multiple host records match, find the one with matching IP."""
        for each in ib_obj_ref:
            if each.get('ipv4addrs') and proposed_object and proposed_object.get('ipv4addrs'):
                if each['ipv4addrs'][0].get('ipv4addr') == proposed_object['ipv4addrs'][0].get('ipv4addr'):
                    return each
        # Fallback
        return obj_filter

    def post_prepare(self, proposed_object, current_object, ib_obj_type):
        """Handle configure_for_dns bypass and ipv4addrs idempotency."""
        # If configure_by_dns is False and view is 'default', remove the default dns view
        if not proposed_object.get('configure_for_dns') and proposed_object.get('view') == 'default':
            proposed_object.pop('view', None)

        # Validate use_for_ea_inheritance
        if 'ipv4addrs' in proposed_object:
            if sum(addr.get('use_for_ea_inheritance', False) for addr in proposed_object['ipv4addrs']) > 1:
                raise Exception('Only one address allowed to be used for extensible attributes inheritance')

        # Idempotency: remove add/remove flags if IP already exists/doesn't exist
        self._handle_add_remove_idempotency(proposed_object, current_object)

        # Check for new_ipv4addr
        proposed_object = self._check_for_new_ipv4addr(proposed_object)

        return proposed_object

    def _handle_add_remove_idempotency(self, proposed_object, current_object):
        """Handle add/remove idempotency for ipv4addrs."""
        if 'ipv4addrs' not in proposed_object or 'ipv4addrs' not in current_object:
            return

        check_remove = []
        for each in current_object.get('ipv4addrs', []):
            if each.get('ipv4addr') == proposed_object['ipv4addrs'][0].get('ipv4addr'):
                if 'add' in proposed_object['ipv4addrs'][0]:
                    del proposed_object['ipv4addrs'][0]['add']
                    break
            check_remove += each.values()

        if proposed_object['ipv4addrs'][0].get('ipv4addr') not in check_remove:
            if 'remove' in proposed_object['ipv4addrs'][0]:
                del proposed_object['ipv4addrs'][0]['remove']

    def _check_for_new_ipv4addr(self, proposed_object):
        """Check if new_ipv4addr parameter is passed for static IP update."""

        if 'ipv4addr' in proposed_object:
            if isinstance(proposed_object['ipv4addr'], str) and 'new_ipv4addr' in proposed_object['ipv4addr']:
                new_ipv4 = check_type_dict(proposed_object['ipv4addr'])['new_ipv4addr']
                proposed_object['ipv4addr'] = new_ipv4

        return proposed_object

    def check_if_nios_next_ip_exists(self, wapi, proposed_object):
        """Format ipv4addrs for next_available_ip allocation."""
        from ..connector import NIOS_NEXT_AVAILABLE_IP

        if 'ipv4addrs' in proposed_object:
            if isinstance(proposed_object['ipv4addrs'][0].get('ipv4addr'), str) and \
               'nios_next_ip' in proposed_object['ipv4addrs'][0]['ipv4addr']:
                ip_range = check_type_dict(proposed_object['ipv4addrs'][0]['ipv4addr'])['nios_next_ip']
                proposed_object['ipv4addrs'][0]['ipv4addr'] = NIOS_NEXT_AVAILABLE_IP + ':' + ip_range

        return proposed_object

    def pre_update(self, wapi, ref, proposed_object, current_object, ib_spec, module, ib_obj_type):
        """Handle host record update with add/remove IP and use_for_ea_inheritance."""
        run_update = True
        proposed_object = self.on_update(proposed_object, ib_spec)

        if 'ipv4addrs' in proposed_object:
            if 'add' in proposed_object['ipv4addrs'][0] or 'remove' in proposed_object['ipv4addrs'][0]:
                run_update, proposed_object = self._check_if_add_remove_ip_arg_exists(proposed_object)
                if not run_update:
                    return None  # Skip update

        # Remove use_for_ea_inheritance before update (handled separately after)
        if 'ipv4addrs' in proposed_object:
            update_proposed = copy.deepcopy(proposed_object)
            update_proposed['ipv4addrs'] = [
                {k: v for k, v in addr.items() if k != 'use_for_ea_inheritance'}
                for addr in proposed_object['ipv4addrs']
            ]
            return ref, update_proposed
        else:
            return ref, proposed_object

    def post_update(self, wapi, ref, res, proposed_object):
        """Handle use_for_ea_inheritance after main update."""
        if not res or 'ipv4addrs' not in proposed_object:
            return

        # WAPI resets use_for_ea_inheritance on each update
        host_ref = wapi.connector.get_object(obj_type=str(res), return_fields=['ipv4addrs'])
        if host_ref and 'ipv4addrs' in host_ref:
            ref_dict = {obj['ipv4addr']: obj['_ref'] for obj in host_ref['ipv4addrs']}
            sorted_ipv4addrs = sorted(
                proposed_object['ipv4addrs'],
                key=lambda x: x.get('use_for_ea_inheritance', False)
            )
            for proposed in sorted_ipv4addrs:
                ipv4addr = proposed['ipv4addr']
                if ipv4addr in ref_dict and 'use_for_ea_inheritance' in proposed:
                    wapi.update_object(ref_dict[ipv4addr],
                                       {'use_for_ea_inheritance': proposed['use_for_ea_inheritance']})

    def _check_if_add_remove_ip_arg_exists(self, proposed_object):
        """Process add/remove IP arguments for host records."""
        update = False
        if 'add' in proposed_object['ipv4addrs'][0]:
            if proposed_object['ipv4addrs'][0]['add']:
                proposed_object['ipv4addrs+'] = proposed_object['ipv4addrs']
                del proposed_object['ipv4addrs']
                del proposed_object['ipv4addrs+'][0]['add']
                update = True
            else:
                del proposed_object['ipv4addrs'][0]['add']
        elif 'remove' in proposed_object['ipv4addrs'][0]:
            if proposed_object['ipv4addrs'][0]['remove']:
                proposed_object['ipv4addrs-'] = proposed_object['ipv4addrs']
                del proposed_object['ipv4addrs']
                del proposed_object['ipv4addrs-'][0]['remove']
                update = True
            else:
                del proposed_object['ipv4addrs'][0]['remove']
        return update, proposed_object

    def get_object_ref(self, wapi, module, ib_obj_type, obj_filter, ib_spec):
        """Custom object ref lookup for host records."""

        update = False
        new_name = None

        if 'name' not in obj_filter:
            return wapi.get_object('record:host', obj_filter.copy(),
                                   return_fields=list(ib_spec.keys())), update, new_name

        # Check for old_name/new_name rename
        try:
            name_obj = check_type_dict(obj_filter['name'])
            old_name = name_obj['old_name'].lower()
            new_name = name_obj['new_name'].lower()
        except TypeError:
            old_name = None
            new_name = None

        return_fields = list(ib_spec.keys())
        # Add ipv4addrs/ipv6addrs sub-fields
        ipv4addrs_return = [
            'ipv4addrs.ipv4addr', 'ipv4addrs.mac', 'ipv4addrs.configure_for_dhcp', 'ipv4addrs.host',
            'ipv4addrs.nextserver', 'ipv4addrs.use_nextserver', 'ipv4addrs.use_for_ea_inheritance'
        ]
        ipv6addrs_return = [
            'ipv6addrs.ipv6addr', 'ipv6addrs.duid', 'ipv6addrs.configure_for_dhcp', 'ipv6addrs.host'
        ]
        return_fields.extend(ipv4addrs_return)
        return_fields.extend(ipv6addrs_return)

        if old_name and new_name:
            if not obj_filter.get('configure_for_dns', True):
                test_obj_filter = dict([('name', old_name)])
            else:
                test_obj_filter = dict([('name', old_name), ('view', obj_filter['view'])])

            ib_obj = wapi.get_object('record:host', test_obj_filter, return_fields=return_fields)
            if ib_obj:
                obj_filter['name'] = new_name
            else:
                raise Exception("object with name: '%s' is not found" % old_name)
            update = True
            return ib_obj, update, new_name

        # Normal lookup
        name = obj_filter['name']
        if not obj_filter.get('configure_for_dns', True):
            test_obj_filter = dict([('name', name)])
        else:
            test_obj_filter = dict([('name', name), ('view', obj_filter['view'])])

        ib_obj = wapi.get_object('record:host', test_obj_filter, return_fields=return_fields)
        return ib_obj, update, new_name
