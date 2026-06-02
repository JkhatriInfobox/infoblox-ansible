from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from .base import BaseObjectHandler

# Lazy-initialized registry mapping NIOS object types to handler instances.
_HANDLER_REGISTRY = {}
_registry_initialized = False


def _init_registry():
    """Initialize the handler registry once on first use.

    Lazy initialization avoids circular imports between the handlers,
    the connector constants, and api.py.
    """
    global _registry_initialized
    if _registry_initialized:
        return

    from .host_record import HostRecordHandler
    from .a_record import ARecordHandler
    from .txt_record import TxtRecordHandler
    from .member import MemberHandler
    from .zone import ZoneHandler
    from .range_handler import RangeHandler
    from .network_handler import NetworkHandler
    from .vlan import VlanHandler
    from .extensible_attr import ExtensibleAttributeHandler
    from .dns_record import DnsRecordHandler
    from .fixed_address import FixedAddressHandler
    from ..connector import (
        NIOS_HOST_RECORD, NIOS_A_RECORD, NIOS_AAAA_RECORD,
        NIOS_TXT_RECORD, NIOS_MEMBER, NIOS_ZONE, NIOS_RANGE,
        NIOS_IPV4_NETWORK, NIOS_IPV6_NETWORK,
        NIOS_IPV4_NETWORK_CONTAINER, NIOS_IPV6_NETWORK_CONTAINER,
        NIOS_IPV4_FIXED_ADDRESS, NIOS_IPV6_FIXED_ADDRESS,
        NIOS_VLAN, NIOS_EXTENSIBLE_ATTRIBUTE, NIOS_PTR_RECORD,
        NIOS_SRV_RECORD, NIOS_NAPTR_RECORD,
    )

    _HANDLER_REGISTRY.update({
        NIOS_HOST_RECORD: HostRecordHandler(),
        NIOS_A_RECORD: ARecordHandler(),
        NIOS_AAAA_RECORD: DnsRecordHandler(),
        NIOS_TXT_RECORD: TxtRecordHandler(),
        NIOS_MEMBER: MemberHandler(),
        NIOS_ZONE: ZoneHandler(),
        NIOS_RANGE: RangeHandler(),
        NIOS_IPV4_NETWORK: NetworkHandler(),
        NIOS_IPV6_NETWORK: NetworkHandler(),
        NIOS_IPV4_NETWORK_CONTAINER: NetworkHandler(),
        NIOS_IPV6_NETWORK_CONTAINER: NetworkHandler(),
        NIOS_IPV4_FIXED_ADDRESS: FixedAddressHandler(),
        NIOS_IPV6_FIXED_ADDRESS: FixedAddressHandler(),
        NIOS_VLAN: VlanHandler(),
        NIOS_EXTENSIBLE_ATTRIBUTE: ExtensibleAttributeHandler(),
        NIOS_PTR_RECORD: DnsRecordHandler(),
        NIOS_SRV_RECORD: DnsRecordHandler(),
        NIOS_NAPTR_RECORD: DnsRecordHandler(),
    })

    _registry_initialized = True


def get_handler(ib_obj_type):
    """Get the handler for the given NIOS object type.

    Returns a BaseObjectHandler for any type without a custom handler.
    """
    _init_registry()
    handler = _HANDLER_REGISTRY.get(ib_obj_type)
    if handler is None:
        handler = BaseObjectHandler()
    return handler
