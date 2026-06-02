from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from .base import BaseObjectHandler
from ..transforms import convert_ea_list_to_struct


class ExtensibleAttributeHandler(BaseObjectHandler):
    """Handler for extensibleattributedef objects.

    Handles list_values struct conversion and default_value stringification.
    """

    def post_prepare(self, proposed_object, current_object, ib_obj_type):
        """Convert EA list values and stringify default_value."""
        proposed_object = convert_ea_list_to_struct(proposed_object)

        # Also convert current_object for accurate comparison
        if current_object:
            convert_ea_list_to_struct(current_object)

        # Convert default_value to string for both
        for obj in (proposed_object, current_object or {}):
            if 'default_value' in obj:
                obj['default_value'] = str(obj['default_value'])

        return proposed_object
