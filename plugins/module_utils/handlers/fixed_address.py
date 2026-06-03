from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from .base import BaseObjectHandler


class FixedAddressHandler(BaseObjectHandler):
    """Handler for fixedaddress and ipv6fixedaddress objects.

    Handles MAC/DUID-based lookups and network_view preservation on update.
    """

    def get_object_ref(self, wapi, module, ib_obj_type, obj_filter, ib_spec):
        """Lookup fixed address by MAC or DUID."""
        from ..connector import NIOS_IPV4_FIXED_ADDRESS, NIOS_IPV6_FIXED_ADDRESS

        update = False
        new_name = None
        return_fields = list(ib_spec.keys())

        # Determine object type
        if 'mac' in obj_filter:
            ib_obj_type = NIOS_IPV4_FIXED_ADDRESS
            test_obj_filter = dict([['mac', obj_filter['mac']]])
        elif 'duid' in obj_filter:
            ib_obj_type = NIOS_IPV6_FIXED_ADDRESS
            test_obj_filter = dict([['duid', obj_filter['duid']]])
        else:
            test_obj_filter = obj_filter.copy()
            ib_obj_type = NIOS_IPV4_FIXED_ADDRESS  # default

        ib_obj = wapi.get_object(ib_obj_type, test_obj_filter, return_fields=return_fields)
        return ib_obj, update, new_name

    def post_prepare(self, proposed_object, current_object, ib_obj_type):
        """Strip DHCP options with use_option=False from both sides to prevent false idempotency failures."""
        if proposed_object.get('options') is not None or current_object.get('options') is not None:
            if proposed_object.get('options'):
                proposed_object['options'] = [
                    opt for opt in proposed_object['options']
                    if opt.get('use_option', True)
                ]
            if current_object.get('options'):
                current_object['options'] = [
                    opt for opt in current_object['options']
                    if opt.get('use_option', True)
                ]
        return proposed_object

    def pre_update(self, wapi, ref, proposed_object, current_object, ib_spec, module, ib_obj_type):
        """Keep network_view for fixed addresses (unlike other types)."""
        proposed_object = self.on_update(proposed_object, ib_spec)
        return ref, proposed_object
