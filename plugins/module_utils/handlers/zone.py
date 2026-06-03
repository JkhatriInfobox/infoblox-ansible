from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from .base import BaseObjectHandler


class ZoneHandler(BaseObjectHandler):
    """Handler for zone_auth objects.

    Handles restart_if_needed non-searchable field and zone_format non-updatable field.
    """

    def get_object_ref(self, wapi, module, ib_obj_type, obj_filter, ib_spec):
        """Custom lookup that removes restart_if_needed from search fields."""
        update = False
        new_name = None
        return_fields = list(ib_spec.keys())

        # Remove non-searchable field
        temp = ib_spec.get('restart_if_needed')
        if 'restart_if_needed' in ib_spec:
            del ib_spec['restart_if_needed']
            return_fields = list(ib_spec.keys())

        ib_obj = wapi.get_object('zone_auth', obj_filter.copy(), return_fields=return_fields)

        # Always reinstate restart_if_needed so prepare_proposed includes it.
        # Previously this was only reinstated when the object was not found,
        # silently dropping the field on every zone update.
        if temp is not None:
            ib_spec['restart_if_needed'] = temp

        return ib_obj, update, new_name

    def pre_update(self, wapi, ref, proposed_object, current_object, ib_spec, module, ib_obj_type):
        """Remove zone_format before update (not supported)."""
        proposed_object = self.on_update(proposed_object, ib_spec)
        proposed_object.pop('zone_format', None)
        return ref, proposed_object
