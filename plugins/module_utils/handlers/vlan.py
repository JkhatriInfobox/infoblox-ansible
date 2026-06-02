from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from .base import BaseObjectHandler


class VlanHandler(BaseObjectHandler):
    """Handler for vlan objects.

    Handles parent reference resolution and empty key cleanup.
    """

    def build_object_filter(self, module, ib_spec):
        """Include parent transform in filter for VLAN lookups."""
        obj_filter = dict([(k, module.params[k]) for k, v in ib_spec.items() if v.get('ib_req')])
        if 'parent' in ib_spec and 'transform' in ib_spec['parent']:
            obj_filter['parent'] = ib_spec['parent']['transform'](module)
        return obj_filter

    def resolve_current(self, ib_obj_ref, obj_filter, proposed_object=None):
        """Resolve VLAN current object with parent _ref normalization."""
        current_object, ref = super(VlanHandler, self).resolve_current(
            ib_obj_ref, obj_filter, proposed_object)

        # Normalize parent field to just the _ref string
        if ib_obj_ref and 'parent' in current_object:
            if isinstance(current_object['parent'], dict):
                current_object['parent'] = current_object['parent']['_ref']

        return current_object, ref

    def post_prepare(self, proposed_object, current_object, ib_obj_type):
        """Clean empty keys that don't exist in current object."""
        return self._clean_empty_keys(current_object, proposed_object)

    def _clean_empty_keys(self, current_object, proposed_object):
        """Remove keys from proposed that are empty and absent from current."""
        keys_to_remove = []
        for key, proposed_item in proposed_object.items():
            if proposed_item in [None, '', [], {}, set()]:
                if key not in current_object:
                    keys_to_remove.append(key)
        for key in keys_to_remove:
            del proposed_object[key]
        return proposed_object
