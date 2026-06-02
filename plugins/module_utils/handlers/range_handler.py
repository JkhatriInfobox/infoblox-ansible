from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from .base import BaseObjectHandler


class RangeHandler(BaseObjectHandler):
    """Handler for range objects.

    Handles new_start_addr/new_end_addr for range updates.
    """

    def post_prepare(self, proposed_object, current_object, ib_obj_type):
        """Replace new_start_addr/new_end_addr with start_addr/end_addr."""
        if proposed_object.get('new_start_addr'):
            proposed_object['start_addr'] = proposed_object.pop('new_start_addr')
        if proposed_object.get('new_end_addr'):
            proposed_object['end_addr'] = proposed_object.pop('new_end_addr')

        # Remove use_options=False entries for comparison
        if proposed_object.get('options'):
            proposed_object['options'] = [
                option for option in proposed_object['options']
                if option.get('use_option', True)
            ]

        return proposed_object

    def get_object_ref(self, wapi, module, ib_obj_type, obj_filter, ib_spec):
        """Custom lookup that removes new_start_addr/new_end_addr from search."""
        update = False
        new_name = None

        # Remove update-only fields
        new_start = ib_spec.get('new_start_addr')
        new_end = ib_spec.get('new_end_addr')
        if 'new_start_addr' in ib_spec:
            del ib_spec['new_start_addr']
        if 'new_end_addr' in ib_spec:
            del ib_spec['new_end_addr']

        new_start_arg = module.params.get('new_start_addr')
        new_end_arg = module.params.get('new_end_addr')

        return_fields = list(ib_spec.keys())
        ib_obj = wapi.get_object('range', obj_filter.copy(), return_fields=return_fields)

        # Restore the keys
        if new_start:
            ib_spec['new_start_addr'] = new_start
        if new_end:
            ib_spec['new_end_addr'] = new_end

        # Validate range exists for updates
        if new_start_arg and new_end_arg:
            if not ib_obj:
                raise Exception(
                    'Specified range %s-%s not found' % (obj_filter.get('start_addr'), obj_filter.get('end_addr')))

        return ib_obj, update, new_name
