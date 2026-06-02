from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

# Imported at module load (before unit tests patch it) so that the binding
# matches the original api.py behaviour. A call-time import would pick up the
# test's patched MagicMock and break plain-string name handling.
from ansible.module_utils.common.validation import check_type_dict


class BaseObjectHandler(object):
    """Default CRUD handler for NIOS object types.

    Subclass and override methods to customize behavior for specific
    object types without modifying the shared run() logic.
    """

    def build_object_filter(self, module, ib_spec):
        """Build the filter dict used to find existing objects.

        Default: all params marked with ib_req=True.
        """
        return dict([(k, module.params[k]) for k, v in ib_spec.items() if v.get('ib_req')])

    def get_object_ref(self, wapi, module, ib_obj_type, obj_filter, ib_spec):
        """Find existing object reference.

        Handles the generic rename case where ``name`` is supplied as a
        ``{'old_name': ..., 'new_name': ...}`` dict, looking up the object by
        ``old_name`` and signalling an update with the resolved ``new_name``.

        Returns:
            tuple: (ib_obj_ref_list, update_flag, new_name)
        """
        from ..connector import NIOS_NETWORK_VIEW, NIOS_VLAN, NIOS_ADMINUSER

        update = False
        new_name = None
        return_fields = list(ib_spec.keys())

        # Password is write-only and must not be requested back from the API.
        if ib_obj_type == NIOS_ADMINUSER and 'password' in return_fields:
            return_fields.remove('password')

        # VLAN lookups must include the resolved parent reference.
        if ib_obj_type == NIOS_VLAN and 'parent' in ib_spec and 'transform' in ib_spec['parent']:
            obj_filter['parent'] = ib_spec['parent']['transform'](module)

        if 'name' in obj_filter:
            old_name = None
            try:
                name_obj = check_type_dict(obj_filter['name'])
                # network_view supports searching/updating with camelCase, so
                # its names must not be lower-cased.
                if ib_obj_type == NIOS_NETWORK_VIEW:
                    old_name = name_obj['old_name']
                    new_name = name_obj['new_name']
                else:
                    old_name = name_obj['old_name'].lower()
                    new_name = name_obj['new_name'].lower()
            except TypeError:
                old_name = None
                new_name = None

            if old_name and new_name:
                if ib_obj_type == NIOS_VLAN:
                    test_obj_filter = dict([('name', old_name),
                                            ('id', obj_filter.get('id')),
                                            ('parent', obj_filter.get('parent'))])
                else:
                    test_obj_filter = dict([('name', old_name)])

                ib_obj = wapi.get_object(ib_obj_type, test_obj_filter, return_fields=return_fields)
                if ib_obj:
                    obj_filter['name'] = new_name
                else:
                    raise Exception("object with name: '%s' is not found" % old_name)
                update = True
                return ib_obj, update, new_name

        ib_obj = wapi.get_object(ib_obj_type, obj_filter.copy(), return_fields=return_fields)
        return ib_obj, update, new_name

    def resolve_current(self, ib_obj_ref, obj_filter, proposed_object=None):
        """Resolve the current object and its _ref from the query result.

        Returns:
            tuple: (current_object, ref)
        """
        from ..transforms import flatten_extattrs

        if ib_obj_ref:
            if len(ib_obj_ref) > 1:
                current_object = self._resolve_multiple_refs(ib_obj_ref, obj_filter, proposed_object)
            else:
                current_object = ib_obj_ref[0]

            if 'extattrs' in current_object:
                current_object['extattrs'] = flatten_extattrs(current_object['extattrs'])

            ref = current_object.pop('_ref', None)
        else:
            current_object = obj_filter
            ref = None

        return current_object, ref

    def _resolve_multiple_refs(self, ib_obj_ref, obj_filter, proposed_object):
        """When multiple objects match, pick the correct one."""
        return ib_obj_ref[0]

    def prepare_proposed(self, module, ib_spec, current_object=None):
        """Build proposed object from module params and transforms."""
        proposed_object = {}
        for key, value in ib_spec.items():
            if module.params[key] is not None:
                if 'transform' in value:
                    proposed_object[key] = value['transform'](module)
                else:
                    proposed_object[key] = module.params[key]
            elif 'transform' in value:
                transformed_value = value['transform'](module)
                if transformed_value is not None:
                    proposed_object[key] = transformed_value
        return proposed_object

    def post_prepare(self, proposed_object, current_object, ib_obj_type):
        """Hook after prepare_proposed, before comparison.

        Used for type-specific normalization.
        """
        return proposed_object

    def pre_create(self, wapi, proposed_object, ib_obj_type):
        """Hook before create. Return the (possibly modified) proposed_object."""
        return proposed_object

    def pre_update(self, wapi, ref, proposed_object, current_object, ib_spec, module, ib_obj_type):
        """Hook before update. Return (ref, proposed_object) or None to skip update."""
        proposed_object = self.on_update(proposed_object, ib_spec)
        # network_view is not updatable for generic object types. Handlers for
        # fixed addresses and ranges override this to preserve it.
        if 'network_view' in proposed_object:
            proposed_object.pop('network_view')
        return ref, proposed_object

    def pre_delete(self, wapi, ref, proposed_object):
        """Hook before delete. Return ref or None to skip."""
        return ref

    def on_update(self, proposed_object, ib_spec):
        """Filter out non-updatable fields."""
        keys = set()
        for key, value in proposed_object.items():
            if key in ib_spec:
                update = ib_spec[key].get('update', True)
                if not update:
                    keys.add(key)
        return dict([(k, v) for k, v in proposed_object.items() if k not in keys])

    def compare(self, current_object, proposed_object, ib_obj_type=None):
        """Compare current vs proposed objects.

        Returns True if objects are equal (no update needed).
        Default delegates to the shared compare_objects logic.
        """
        # Import here to avoid circular imports during initial setup
        from ..comparators import compare_objects
        return compare_objects(current_object, proposed_object, ib_obj_type)
