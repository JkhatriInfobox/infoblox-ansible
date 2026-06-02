from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
from ast import literal_eval as safe_eval


def normalize_extattrs(value):
    """Normalize extattrs field to expected format for WAPI.

    Transforms key/value pairs into:
        extattrs: { key: { value: <value> } }
    """
    return dict([(k, {'value': v}) for k, v in value.items()])


def flatten_extattrs(value):
    """Flatten WAPI extattrs response to simple key/value pairs.

    Transforms:
        extattrs: { key: { value: <value> } }
    Into:
        extattrs: { key: value }
    """
    return dict([(k, v['value']) for k, v in value.items()])


def member_normalize(member_spec):
    """Transform member module arguments into a valid WAPI struct.

    Removes None values and converts list-wrapped dicts to plain dicts
    for specific member elements.
    """
    member_elements = ['vip_setting', 'ipv6_setting', 'lan2_port_setting', 'mgmt_port_setting',
                       'pre_provisioning', 'network_setting', 'v6_network_setting',
                       'ha_port_setting', 'lan_port_setting', 'lan2_physical_setting',
                       'lan_ha_port_setting', 'mgmt_network_setting', 'v6_mgmt_network_setting']
    for key in list(member_spec.keys()):
        if key in member_elements and member_spec[key] is not None:
            member_spec[key] = member_spec[key][0]
        if isinstance(member_spec[key], dict):
            member_spec[key] = member_normalize(member_spec[key])
        elif isinstance(member_spec[key], list):
            for x in member_spec[key]:
                if isinstance(x, dict):
                    x = member_normalize(x)
        elif member_spec[key] is None:
            del member_spec[key]
    return member_spec


def convert_members_to_struct(member_spec):
    """Transform members list into WAPI dhcpmember struct format."""
    if 'members' in member_spec.keys():
        member_spec['members'] = [{'_struct': 'dhcpmember', 'name': k['name']} for k in member_spec['members']]
    return member_spec


def convert_ea_list_to_struct(member_spec):
    """Transform list_values into WAPI extensibleattributedef struct format."""
    if 'list_values' in member_spec.keys():
        if all(isinstance(item, dict) for item in member_spec['list_values']):
            member_spec['list_values'] = [item['value'] for item in member_spec['list_values']]
        member_spec['list_values'] = [
            {'_struct': 'extensibleattributedef:listvalues', 'value': v}
            for v in member_spec['list_values']
        ]
    return member_spec


def normalize_ib_spec(ib_spec):
    """Normalize ib_spec to standard Ansible argument_spec format.

    Strips internal keys (ib_req, transform, update) that are not valid
    for AnsibleModule argument_spec.
    """
    result = {}
    for arg in ib_spec:
        result[arg] = dict([(k, v)
                            for k, v in ib_spec[arg].items()
                            if k not in ('ib_req', 'transform', 'update')])
    return result


def parse_txt_field(text_obj):
    """Parse TXT record text field, handling old_text/new_text dict format.

    Returns:
        tuple: (text_value, old_text_exists)
    """
    old_text_exists = False
    if text_obj.startswith("{"):
        try:
            parsed = json.loads(text_obj)
            txt = parsed['new_text']
            old_text_exists = True
        except Exception:
            try:
                parsed = safe_eval(text_obj)
                txt = parsed['new_text']
                old_text_exists = True
            except Exception:
                raise TypeError('unable to evaluate string as dictionary')
    else:
        txt = text_obj
    return txt, old_text_exists


def parse_txt_for_lookup(text_obj):
    """Parse TXT record text field for object lookup (old_text extraction).

    Returns:
        tuple: (lookup_text, old_text_exists)
    """
    old_text_exists = False
    if text_obj.startswith("{"):
        try:
            parsed = json.loads(text_obj)
            txt = parsed['old_text']
            old_text_exists = True
        except Exception:
            try:
                parsed = safe_eval(text_obj)
                txt = parsed['old_text']
                old_text_exists = True
            except Exception:
                raise TypeError('unable to evaluate string as dictionary')
    else:
        txt = text_obj
    return txt, old_text_exists
