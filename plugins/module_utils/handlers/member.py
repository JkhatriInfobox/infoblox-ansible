from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from .base import BaseObjectHandler
from ..transforms import member_normalize


class MemberHandler(BaseObjectHandler):
    """Handler for member objects.

    Handles host_name rename, create_token, and member normalization.
    """

    def post_prepare(self, proposed_object, current_object, ib_obj_type):
        """Normalize member attributes and handle create_token."""
        proposed_object = member_normalize(proposed_object)
        # Remove create_token if not set to True (WAPI never returns it)
        if proposed_object.get("create_token") is not True:
            proposed_object.pop("create_token", None)
        return proposed_object

    def get_object_ref(self, wapi, module, obj_filter, ib_spec):
        """Custom lookup for member objects with host_name rename support."""
        from ansible.module_utils.common.validation import check_type_dict

        update = False
        new_name = None
        return_fields = list(ib_spec.keys())

        # Remove non-searchable fields
        temp_create_token = ib_spec.get('create_token')
        if 'create_token' in ib_spec:
            del ib_spec['create_token']
            return_fields = list(ib_spec.keys())

        try:
            name_obj = check_type_dict(obj_filter['host_name'])
            old_name = name_obj['old_name']
            new_name = name_obj['new_name']
        except TypeError:
            old_name = None
            new_name = None

        if old_name and new_name:
            test_obj_filter = obj_filter.copy()
            test_obj_filter['host_name'] = old_name
            ib_obj = wapi.get_object('member', test_obj_filter.copy(), return_fields=return_fields)
            if ib_obj:
                obj_filter['host_name'] = new_name
            else:
                raise Exception("object with name: '%s' is not found" % old_name)
            update = True
            # Reinstate create_token
            if temp_create_token is not None:
                ib_spec['create_token'] = temp_create_token
            return ib_obj, update, new_name
        else:
            ib_obj = wapi.get_object('member', obj_filter.copy(), return_fields=return_fields)

        # Reinstate create_token
        if temp_create_token is not None:
            ib_spec['create_token'] = temp_create_token

        return ib_obj, update, new_name

    def pre_update(self, wapi, ref, proposed_object, current_object, ib_spec, module):
        """Handle create_token function call and normal member updates."""
        # If create_token is True, call the function instead of updating
        if proposed_object.get("create_token") is True:
            return 'create_token', ref  # Signal to call func instead of update

        proposed_object = self.on_update(proposed_object, ib_spec)
        return ref, proposed_object
