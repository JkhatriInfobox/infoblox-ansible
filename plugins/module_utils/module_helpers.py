from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from .api import WapiModule, normalize_ib_spec


def build_argument_spec(ib_spec, extra_spec=None):
    """Build a standard Ansible argument_spec for a NIOS module.

    Combines the common provider/state options with the module-specific
    ib_spec and the shared provider spec. Replaces the ~6-line boilerplate
    block duplicated across all NIOS modules.

    :param ib_spec: the module-specific Infoblox spec dict
    :param extra_spec: optional dict of additional top-level argument options
    :returns: a complete argument_spec dict ready for AnsibleModule
    """
    argument_spec = dict(
        provider=dict(required=True),
        state=dict(default='present', choices=['present', 'absent'])
    )
    if extra_spec:
        argument_spec.update(extra_spec)
    argument_spec.update(normalize_ib_spec(ib_spec))
    argument_spec.update(WapiModule.provider_spec)
    return argument_spec


def resolve_ref(wapi, module, obj_type, obj_filter, label=None, fail_msg=None):
    """Resolve a NIOS object reference (_ref) by querying WAPI.

    Consolidates the repeated pattern:
        obj = wapi.get_object(obj_type, obj_filter)
        if obj:
            return obj[0]['_ref']
        else:
            module.fail_json(msg='... cannot be found.')

    :param wapi: the WapiModule instance
    :param module: the AnsibleModule instance
    :param obj_type: the NIOS object type string (e.g. 'dtc:topology')
    :param obj_filter: dict filter to find the object
    :param label: human-readable name used in the failure message
    :param fail_msg: optional custom failure message (overrides label)
    :returns: the _ref string of the matching object
    """
    obj = wapi.get_object(obj_type, obj_filter)
    if obj:
        return obj[0]['_ref']

    if fail_msg is None:
        name = label if label is not None else obj_filter
        fail_msg = '%s cannot be found.' % name
    module.fail_json(msg=fail_msg)


def topology_ref_transform(wapi, module, param_name='topology'):
    """Resolve a dtc:topology object _ref from a module parameter.

    Shared helper for the duplicated topology_transform() functions in
    nios_dtc_lbdn and nios_dtc_pool.

    :param wapi: the WapiModule instance
    :param module: the AnsibleModule instance
    :param param_name: the module param holding the topology name
    :returns: the topology _ref, or None if the param is unset
    """
    topology = module.params.get(param_name)
    if topology:
        return resolve_ref(wapi, module, 'dtc:topology', {'name': topology},
                           label='topology %s' % topology)
    return None
