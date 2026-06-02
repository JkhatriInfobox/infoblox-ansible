from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
# This code is part of Ansible, but is an independent component.
# This particular file snippet, and this file snippet only, is BSD licensed.
# Modules you write using this snippet, which is embedded dynamically by Ansible
# still belong to the author of the module, and may assign their own license
# to the complete work.
#
#  2020 Infoblox IncCopyright 
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

from functools import partial

from ansible.module_utils.common.text.converters import to_native
from ansible.module_utils.common.text.converters import to_text
from ansible.module_utils.common.validation import check_type_dict

try:
    from infoblox_client.exceptions import InfobloxException
    HAS_INFOBLOX_CLIENT = True
except ImportError:
    HAS_INFOBLOX_CLIENT = False

# Re-export all constants and utilities from their new modules for backward compatibility.
# Any module importing from api.py continues to work unchanged.
from .connector import (                               # noqa: F401
    NIOS_DNS_VIEW, NIOS_NETWORK_VIEW, NIOS_HOST_RECORD,
    NIOS_IPV4_NETWORK, NIOS_RANGE, NIOS_IPV6_NETWORK, NIOS_ZONE,
    NIOS_PTR_RECORD, NIOS_A_RECORD, NIOS_AAAA_RECORD, NIOS_CNAME_RECORD,
    NIOS_MX_RECORD, NIOS_SRV_RECORD, NIOS_NAPTR_RECORD, NIOS_TXT_RECORD,
    NIOS_NSGROUP, NIOS_IPV4_FIXED_ADDRESS, NIOS_IPV6_FIXED_ADDRESS,
    NIOS_NEXT_AVAILABLE_IP, NIOS_IPV4_NETWORK_CONTAINER,
    NIOS_IPV6_NETWORK_CONTAINER, NIOS_MEMBER, NIOS_DTC_SERVER,
    NIOS_DTC_POOL, NIOS_DTC_LBDN, NIOS_NSGROUP_FORWARDSTUBSERVER,
    NIOS_NSGROUP_FORWARDINGMEMBER, NIOS_NSGROUP_DELEGATION,
    NIOS_NSGROUP_STUBMEMBER, NIOS_DTC_MONITOR_HTTP, NIOS_DTC_MONITOR_ICMP,
    NIOS_DTC_MONITOR_PDP, NIOS_DTC_MONITOR_SIP, NIOS_DTC_MONITOR_SNMP,
    NIOS_DTC_MONITOR_TCP, NIOS_DTC_TOPOLOGY, NIOS_EXTENSIBLE_ATTRIBUTE,
    NIOS_VLAN, NIOS_ADMINUSER, NIOS_PROVIDER_SPEC, get_connector,
)
from .transforms import (                              # noqa: F401
    normalize_extattrs, flatten_extattrs, member_normalize,
    convert_members_to_struct, convert_ea_list_to_struct, normalize_ib_spec,
)
from .comparators import compare_objects               # noqa: F401
from .handlers.registry import get_handler


class AnsibleError(Exception):
    """Implements raising exceptions."""
    pass


class WapiBase(object):
    """Base class for implementing Infoblox WAPI API."""
    provider_spec = {'provider': dict(type='dict', options=NIOS_PROVIDER_SPEC)}

    def __init__(self, provider):
        self.connector = get_connector(**provider)

    def __getattr__(self, name):
        try:
            return self.__dict__[name]
        except KeyError:
            if name.startswith('_'):
                raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, name))
            return partial(self._invoke_method, name)

    def _invoke_method(self, name, *args, **kwargs):
        try:
            method = getattr(self.connector, name)
            return method(*args, **kwargs)
        except InfobloxException as exc:
            if hasattr(self, 'handle_exception'):
                self.handle_exception(name, exc)
            else:
                raise


class WapiLookup(WapiBase):
    """Implements WapiBase for lookup plugins."""
    def handle_exception(self, method_name, exc):
        if ('text' in exc.response):
            raise Exception(exc.response['text'])
        else:
            raise Exception(exc)


class WapiInventory(WapiBase):
    """Implements WapiBase for dynamic inventory script."""
    pass


class WapiModule(WapiBase):
    """Implements WapiBase for executing a NIOS module."""

    def __init__(self, module):
        self.module = module
        provider = module.params['provider']
        try:
            super(WapiModule, self).__init__(provider)
        except Exception as exc:
            self.module.fail_json(msg=to_text(exc))

    def handle_exception(self, method_name, exc):
        """Gracefully fail the module on InfobloxException."""
        if ('text' in exc.response):
            self.module.fail_json(
                msg=exc.response['text'],
                type=exc.response['Error'].split(':')[0],
                code=exc.response.get('code'),
                operation=method_name
            )
        else:
            self.module.fail_json(msg=to_native(exc))

    def run(self, ib_obj_type, ib_spec):
        """Run the module and perform configuration tasks.

        :args ib_obj_type: the WAPI object type to operate against
        :args ib_spec: the specification for the WAPI object as a dict
        :returns: result dict
        """
        state = self.module.params['state']
        if state not in ('present', 'absent'):
            self.module.fail_json(msg='state must be one of `present`, `absent`, got `%s`' % state)

        result = {'changed': False}

        handler = get_handler(ib_obj_type)

        # Build object filter and find existing object
        obj_filter = handler.build_object_filter(self.module, ib_spec)
        try:
            ib_obj_ref, update, new_name = handler.get_object_ref(
                self, self.module, ib_obj_type, obj_filter, ib_spec)
        except Exception as exc:
            self.module.fail_json(msg=to_native(exc))
            return result

        # For NIOS_RANGE: check with new addresses if not found
        if ib_obj_type == NIOS_RANGE and (ib_obj_ref is None or len(ib_obj_ref) == 0):
            if self.module.params.get('new_start_addr'):
                obj_filter['start_addr'] = self.module.params.get('new_start_addr')
            if self.module.params.get('new_end_addr'):
                obj_filter['end_addr'] = self.module.params.get('new_end_addr')
            try:
                ib_obj_ref, update, new_name = handler.get_object_ref(
                    self, self.module, ib_obj_type, obj_filter, ib_spec)
            except Exception as exc:
                self.module.fail_json(msg=to_native(exc))
                return result

        # Build proposed object from params
        proposed_object = handler.prepare_proposed(self.module, ib_spec)

        # Handle rename
        if update and new_name:
            if ib_obj_type == NIOS_MEMBER:
                proposed_object['host_name'] = new_name
            else:
                proposed_object['name'] = new_name

        # Resolve current object
        current_object, ref = handler.resolve_current(ib_obj_ref, obj_filter, proposed_object)

        # Post-prepare: type-specific normalization
        try:
            proposed_object = handler.post_prepare(proposed_object, current_object, ib_obj_type)
        except AnsibleError as exc:
            self.module.fail_json(msg=to_native(exc))
            return result

        # Normalize extattrs for comparison, then re-normalize for the API call
        if 'extattrs' in proposed_object:
            proposed_object['extattrs'] = normalize_extattrs(proposed_object['extattrs'])

        # Check for nios_next_ip (host record and a_record handlers expose this)
        if hasattr(handler, 'check_if_nios_next_ip_exists'):
            try:
                proposed_object = handler.check_if_nios_next_ip_exists(self, proposed_object)
            except Exception as exc:
                self.module.fail_json(msg=to_native(exc))
                return result

        # Compare current vs proposed
        modified = not handler.compare(current_object, proposed_object, ib_obj_type)

        if state == 'present':
            if ref is None:
                # Create new object
                proposed_object = handler.pre_create(self, proposed_object, ib_obj_type)
                if not self.module.check_mode:
                    self.create_object(ib_obj_type, proposed_object)
                result['changed'] = True

            elif ib_obj_type == NIOS_MEMBER and proposed_object.get("create_token") is True:
                # Special: call create_token function
                proposed_object = None
                result['api_results'] = self.call_func('create_token', ref, proposed_object)
                result['changed'] = True

            elif modified:
                self._check_if_recordname_exists(obj_filter, ib_obj_ref, ib_obj_type,
                                                 current_object, proposed_object)

                update_result = handler.pre_update(self, ref, proposed_object, current_object,
                                                   ib_spec, self.module, ib_obj_type)
                if update_result is None:
                    # Handler signaled skip (e.g., add/remove with flag=False)
                    pass
                else:
                    new_ref, update_proposed = update_result
                    if not self.module.check_mode:
                        res = self.update_object(new_ref, update_proposed)
                        result['changed'] = True
                        # Post-update hook (e.g., host record use_for_ea_inheritance)
                        if hasattr(handler, 'post_update'):
                            handler.post_update(self, ref, res, proposed_object)
                    else:
                        result['changed'] = True

        elif state == 'absent':
            if ref is not None:
                # Handle ipv4addrs remove case for host records
                if 'ipv4addrs' in proposed_object and 'remove' in proposed_object['ipv4addrs'][0]:
                    if hasattr(handler, '_check_if_add_remove_ip_arg_exists'):
                        handler._check_if_add_remove_ip_arg_exists(proposed_object)
                        self.update_object(ref, proposed_object)
                        result['changed'] = True
                elif not self.module.check_mode:
                    delete_ref = handler.pre_delete(self, ref, proposed_object)
                    if delete_ref:
                        self.delete_object(delete_ref)
                        result['changed'] = True

        return result

    def _check_if_recordname_exists(self, obj_filter, ib_obj_ref, ib_obj_type, current_object, proposed_object):
        """Send POST request if record names match but IPs differ."""
        if not ib_obj_ref or ib_obj_type != NIOS_HOST_RECORD:
            return
        if 'name' not in obj_filter or 'name' not in ib_obj_ref[0]:
            return

        obj_host_name = obj_filter['name']
        ref_host_name = ib_obj_ref[0]['name']

        current_ip_addr = proposed_ip_addr = None
        if 'ipv4addrs' in current_object and 'ipv4addrs' in proposed_object:
            current_ip_addr = current_object['ipv4addrs'][0]['ipv4addr']
            proposed_ip_addr = proposed_object['ipv4addrs'][0]['ipv4addr']
        elif 'ipv6addrs' in current_object and 'ipv6addrs' in proposed_object:
            current_ip_addr = current_object['ipv6addrs'][0]['ipv6addr']
            proposed_ip_addr = proposed_object['ipv6addrs'][0]['ipv6addr']

        if current_ip_addr and obj_host_name == ref_host_name and current_ip_addr != proposed_ip_addr:
            self.create_object(ib_obj_type, proposed_object)

    # -------------------------------------------------------------------------
    # Legacy compatibility  kept for any code referencing them directlymethods 
    # -------------------------------------------------------------------------

    def on_update(self, proposed_object, ib_spec):
        """Filter non-updatable fields from proposed object."""
        keys = set()
        for key, value in proposed_object.items():
            if key in ib_spec:
                update = ib_spec[key].get('update', True)
                if not update:
                    keys.add(key)
        return dict([(k, v) for k, v in proposed_object.items() if k not in keys])

    def clean_empty_keys(self, current_object, proposed_object):
        """Remove keys from proposed that are empty and absent from current."""
        keys_to_remove = []
        for key, proposed_item in proposed_object.items():
            if proposed_item in [None, '', [], {}, set()]:
                if key not in current_object:
                    keys_to_remove.append(key)
        for key in keys_to_remove:
            del proposed_object[key]
        return proposed_object

    def compare_objects(self, current_object, proposed_object, ib_obj_type=None):
        """Compare current and proposed objects."""
        return compare_objects(current_object, proposed_object, ib_obj_type)

    def issubset(self, item, objects):
        """Check if item is a subset of objects list."""
        from .comparators import _issubset
        return _issubset(item, objects)

    def compare_extattrs(self, current_extattrs, proposed_extattrs):
        """Compare extensible attributes."""
        from .comparators import _compare_extattrs
        return _compare_extattrs(current_extattrs, proposed_extattrs)

    def verify_list_order(self, proposed_data, current_data):
        """Check if lists are in the same order."""
        from .comparators import _verify_list_order
        return _verify_list_order(proposed_data, current_data)

    def get_network_view(self, proposed_object):
        """Get the network view associated with the dns_view."""
        try:
            network_view_ref = self.get_object('view', {"name": proposed_object['view']},
                                               return_fields=['network_view'])
            if network_view_ref:
                return network_view_ref[0].get('network_view')
        except Exception:
            raise Exception("object with dns_view: %s not found" % proposed_object.get('view'))

    def check_next_ip_status(self, obj_filter):
        """Check if nios_next_ip exists in filter."""
        if 'ipv4addr' in obj_filter:
            if isinstance(obj_filter['ipv4addr'], str) and 'nios_next_ip' in obj_filter['ipv4addr']:
                return True
        return False

    def check_if_nios_next_ip_exists(self, proposed_object):
        """Legacy: format proposed_object for next_available_ip."""
        from .connector import NIOS_NEXT_AVAILABLE_IP

        if 'ipv4addrs' in proposed_object:
            if isinstance(proposed_object['ipv4addrs'][0].get('ipv4addr'), str) and \
               'nios_next_ip' in proposed_object['ipv4addrs'][0]['ipv4addr']:
                ip_range = check_type_dict(proposed_object['ipv4addrs'][0]['ipv4addr'])['nios_next_ip']
                proposed_object['ipv4addrs'][0]['ipv4addr'] = NIOS_NEXT_AVAILABLE_IP + ':' + ip_range
        elif 'ipv4addr' in proposed_object:
            if isinstance(proposed_object['ipv4addr'], str) and 'nios_next_ip' in proposed_object['ipv4addr']:
                ip_range = check_type_dict(proposed_object['ipv4addr'])['nios_next_ip']
                net_view = self.get_network_view(proposed_object)
                proposed_object['ipv4addr'] = NIOS_NEXT_AVAILABLE_IP + ':' + ip_range + ',' + net_view
        return proposed_object

    def check_for_new_ipv4addr(self, proposed_object):
        """Legacy: handle new_ipv4addr in proposed_object."""
        if 'ipv4addr' in proposed_object:
            if isinstance(proposed_object['ipv4addr'], str) and 'new_ipv4addr' in proposed_object['ipv4addr']:
                new_ipv4 = check_type_dict(proposed_object['ipv4addr'])['new_ipv4addr']
                proposed_object['ipv4addr'] = new_ipv4
        return proposed_object

    def check_if_add_remove_ip_arg_exists(self, proposed_object):
        """Legacy: process add/remove IP for host records."""
        update = False
        if 'add' in proposed_object['ipv4addrs'][0]:
            if proposed_object['ipv4addrs'][0]['add']:
                proposed_object['ipv4addrs+'] = proposed_object['ipv4addrs']
                del proposed_object['ipv4addrs']
                del proposed_object['ipv4addrs+'][0]['add']
                update = True
            else:
                del proposed_object['ipv4addrs'][0]['add']
        elif 'remove' in proposed_object['ipv4addrs'][0]:
            if proposed_object['ipv4addrs'][0]['remove']:
                proposed_object['ipv4addrs-'] = proposed_object['ipv4addrs']
                del proposed_object['ipv4addrs']
                del proposed_object['ipv4addrs-'][0]['remove']
                update = True
            else:
                del proposed_object['ipv4addrs'][0]['remove']
        return update, proposed_object

    def get_object_ref(self, module, ib_obj_type, obj_filter, ib_spec):
        """Legacy: delegate to the appropriate handler's get_object_ref."""
        handler = get_handler(ib_obj_type)
        return handler.get_object_ref(self, module, ib_obj_type, obj_filter, ib_spec)
