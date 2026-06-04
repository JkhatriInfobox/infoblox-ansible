from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.module_utils.common.validation import check_type_dict

from .base import BaseObjectHandler
from ..transforms import parse_txt_for_lookup, parse_txt_field


class TxtRecordHandler(BaseObjectHandler):
    """Handler for record:txt objects.

    Handles old_text/new_text updates for TXT records using the shared
    parse_txt_field utility (previously duplicated 3x in api.py).
    """

    def post_prepare(self, proposed_object, current_object, ib_obj_type):
        """Handle new_text field in the text parameter."""
        if 'text' in proposed_object:
            text_obj = proposed_object['text']
            if isinstance(text_obj, str) and text_obj.startswith("{"):
                txt = parse_txt_field(text_obj)[0]
                proposed_object['text'] = txt
        return proposed_object

    def get_object_ref(self, wapi, module, ib_obj_type, obj_filter, ib_spec):
        """Custom lookup handling old_text for TXT records."""
        update = False
        new_name = None
        old_text_exists = False
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
                test_obj_filter = dict([('name', old_name)])
                ib_obj = wapi.get_object('record:txt', test_obj_filter, return_fields=return_fields)
                if ib_obj:
                    obj_filter['name'] = new_name
                else:
                    raise Exception("object with name: '%s' is not found" % old_name)
                update = True
                return ib_obj, update, new_name

            # Normal lookup with text field
            test_obj_filter = obj_filter.copy()
            if 'text' in test_obj_filter:
                try:
                    txt, old_text_exists = parse_txt_for_lookup(test_obj_filter['text'])
                    test_obj_filter['text'] = txt
                except TypeError:
                    pass

            ib_obj = wapi.get_object('record:txt', test_obj_filter.copy(), return_fields=return_fields)

            if old_text_exists and ib_obj is None:
                raise Exception("TXT Record with text: '%s' is not found" % test_obj_filter.get('text'))
        else:
            # No name in filter
            test_obj_filter = obj_filter.copy()
            if 'text' in test_obj_filter:
                try:
                    txt, old_text_exists = parse_txt_for_lookup(test_obj_filter['text'])
                    test_obj_filter['text'] = txt
                except TypeError:
                    pass

            ib_obj = wapi.get_object('record:txt', test_obj_filter.copy(), return_fields=return_fields)
            if old_text_exists and ib_obj is None:
                raise Exception("TXT Record with text: '%s' is not found" % test_obj_filter.get('text'))

        return ib_obj, update, new_name
