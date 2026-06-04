from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from .base import BaseObjectHandler
from ..transforms import convert_members_to_struct


class NetworkHandler(BaseObjectHandler):
    """Handler for network, ipv6network, networkcontainer, ipv6networkcontainer objects.

    Handles template removal, members struct conversion, and options filtering.
    """

    def post_prepare(self, proposed_object, current_object, ib_obj_type):
        """Convert members to struct and filter options."""
        from ..connector import NIOS_IPV4_NETWORK, NIOS_IPV6_NETWORK

        if ib_obj_type in (NIOS_IPV4_NETWORK, NIOS_IPV6_NETWORK):
            proposed_object = convert_members_to_struct(proposed_object)

        # Mirror original api.py behaviour: strip use_option=False entries from
        # BOTH proposed and current before the comparison.  WAPI returns default
        # options (e.g. dhcp-lease-time) with use_option=False; without this the
        # compare always sees a mismatch when the playbook omits `options`.
        if proposed_object.get('options') or current_object.get('options'):
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

    def get_object_ref(self, wapi, module, ib_obj_type, obj_filter, ib_spec):
        """Custom lookup that removes template and container-invalid fields."""
        from ..connector import (
            NIOS_IPV4_NETWORK_CONTAINER,
            NIOS_IPV6_NETWORK_CONTAINER,
            NIOS_IPV4_NETWORK,
            NIOS_IPV6_NETWORK,
        )

        update = False
        new_name = None

        # Remove non-searchable field
        temp_template = ib_spec.get('template')
        if 'template' in ib_spec:
            del ib_spec['template']

        if ib_obj_type in (NIOS_IPV4_NETWORK_CONTAINER, NIOS_IPV6_NETWORK_CONTAINER):
            # Remove fields not valid for containers
            ib_spec.pop('members', None)
            ib_spec.pop('vlans', None)

        return_fields = list(ib_spec.keys())
        ib_obj = wapi.get_object(ib_obj_type, obj_filter.copy(), return_fields=return_fields)

        # For delete operations with implicit default view, perform a second
        # lookup without network_view to detect cross-view ambiguity and support
        # single-object deletion when the default view filter misses.
        if (module.params.get('state') == 'absent' and
                obj_filter.get('network_view') == 'default' and
                ib_obj_type in (NIOS_IPV4_NETWORK, NIOS_IPV6_NETWORK)):
            fallback_filter = obj_filter.copy()
            fallback_filter.pop('network_view', None)
            fallback_ib_obj = wapi.get_object(ib_obj_type, fallback_filter, return_fields=return_fields)
            if fallback_ib_obj and len(fallback_ib_obj) > 1:
                views = sorted(set(obj.get('network_view', 'unknown') for obj in fallback_ib_obj))
                module.fail_json(
                    msg="Multiple networks with CIDR '%s' exist in network views: %s. "
                        "Set network_view explicitly for state=absent."
                        % (obj_filter.get('network'), ', '.join(views))
                )
            if not ib_obj and fallback_ib_obj:
                ib_obj = fallback_ib_obj

        # Reinstate template
        if temp_template is not None:
            ib_spec['template'] = temp_template

        return ib_obj, update, new_name

    def pre_update(self, wapi, ref, proposed_object, current_object, ib_spec, module, ib_obj_type):
        """Handle network_view removal on update."""
        from ..connector import NIOS_IPV4_NETWORK_CONTAINER, NIOS_IPV6_NETWORK_CONTAINER

        proposed_object = self.on_update(proposed_object, ib_spec)

        if 'network_view' in proposed_object:
            proposed_object.pop('network_view')
            if ib_obj_type in (NIOS_IPV4_NETWORK_CONTAINER, NIOS_IPV6_NETWORK_CONTAINER):
                proposed_object.pop('network', None)

        return ref, proposed_object
