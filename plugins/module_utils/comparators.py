from __future__ import (absolute_import, division, print_function)
__metaclass__ = type


def compare_objects(current_object, proposed_object, ib_obj_type=None):
    """Compare current and proposed objects to determine if an update is needed.

    Returns True if objects are equal (no change needed), False otherwise.
    """
    for key, proposed_item in proposed_object.items():
        current_item = current_object.get(key)

        if current_item is None:
            if proposed_item in (None, '', [], {}, set()):
                continue
            return False

        elif isinstance(proposed_item, list):
            if not _compare_list(key, current_item, proposed_item, ib_obj_type):
                return False

        elif isinstance(proposed_item, dict):
            if key == 'extattrs':
                if not _compare_extattrs(current_item, proposed_item):
                    return False
            elif compare_objects(current_item, proposed_item, ib_obj_type) is False:
                return False
            else:
                continue

        else:
            if current_item != proposed_item:
                return False

    return True


def _compare_list(key, current_item, proposed_item, ib_obj_type):
    """Compare list fields. Returns True if equal."""
    from .connector import NIOS_HOST_RECORD, NIOS_DTC_LBDN

    if key == 'aliases':
        if set(current_item) != set(proposed_item):
            return False
        return True

    # Length check for specific list fields
    length_check_keys = ('monitors', 'members', 'options', 'delegate_to',
                         'forwarding_servers', 'stub_members', 'ssh_keys', 'vlans')
    if key in length_check_keys and len(proposed_item) != len(current_item):
        return False

    # Special handling for auth_zones in DTC LBDN
    if key == 'auth_zones' and ib_obj_type == NIOS_DTC_LBDN:
        if len(proposed_item) != len(current_item):
            return False
        current_zones_str = sorted([str(zone) for zone in current_item])
        proposed_zones_str = sorted([str(zone) for zone in proposed_item])
        if current_zones_str != proposed_zones_str:
            return False
        return True

    # Validate sequence for ordered lists
    ordered_keys = ('servers', 'external_servers', 'list_values')
    if key in ordered_keys and not _verify_list_order(proposed_item, current_item):
        return False

    for subitem in proposed_item:
        if not isinstance(subitem, dict):
            continue

        if ib_obj_type == NIOS_HOST_RECORD and key == 'ipv4addrs':
            subitem = _adjust_host_ipv4_subitem(subitem, current_item)

        if not _issubset(subitem, current_item):
            return False

    if key == 'logic_filter_rules' and proposed_item != current_item:
        return False

    return True


def _adjust_host_ipv4_subitem(subitem, current_item):
    """Adjust host record ipv4addrs subitem for comparison."""
    import copy
    subitem = copy.copy(subitem)

    # use_for_ea_inheritance is handled separately in post_update and is not
    # returned by the standard GET — remove it before subset comparison.
    subitem.pop('use_for_ea_inheritance', None)

    if current_item:
        current_config = current_item[0]
        dhcp_flag = current_config.get('configure_for_dhcp', False)
        use_nextserver = subitem.get('use_nextserver', False)

        if not dhcp_flag:
            subitem.pop('use_nextserver', None)
            subitem.pop('nextserver', None)
        elif dhcp_flag and not use_nextserver:
            subitem.pop('nextserver', None)

    return subitem


def _verify_list_order(proposed_data, current_data):
    """Check if two lists have the same elements in the same order."""
    return len(proposed_data) == len(current_data) and all(
        a == b for a, b in zip(proposed_data, current_data))


def _issubset(item, objects):
    """Check if item is a subset of any object in the list."""
    for obj in objects:
        if isinstance(item, dict):
            # Normalize MAC address for comparison
            check_item = item.copy()
            if 'mac' in check_item:
                check_item['mac'] = check_item['mac'].replace('-', ':').lower()
            elif 'duid' in check_item:
                check_item['duid'] = check_item['duid'].replace('-', ':').lower()
            if all(entry in obj.items() for entry in check_item.items()):
                return True
        else:
            if item in obj:
                return True
    return None


def _compare_extattrs(current_extattrs, proposed_extattrs):
    """Compare extensible attributes. Returns True if equal."""
    if len(current_extattrs) != len(proposed_extattrs):
        return False
    for key, proposed_item in proposed_extattrs.items():
        current_item = current_extattrs.get(key)
        if current_item != proposed_item:
            return False
    return True
