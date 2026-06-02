from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
from functools import partial
from ansible.module_utils.basic import env_fallback

try:
    from infoblox_client.connector import Connector
    from infoblox_client.exceptions import InfobloxException
    HAS_INFOBLOX_CLIENT = True
except ImportError:
    HAS_INFOBLOX_CLIENT = False

# NIOS object type constants
NIOS_DNS_VIEW = 'view'
NIOS_NETWORK_VIEW = 'networkview'
NIOS_HOST_RECORD = 'record:host'
NIOS_IPV4_NETWORK = 'network'
NIOS_RANGE = 'range'
NIOS_IPV6_NETWORK = 'ipv6network'
NIOS_ZONE = 'zone_auth'
NIOS_PTR_RECORD = 'record:ptr'
NIOS_A_RECORD = 'record:a'
NIOS_AAAA_RECORD = 'record:aaaa'
NIOS_CNAME_RECORD = 'record:cname'
NIOS_MX_RECORD = 'record:mx'
NIOS_SRV_RECORD = 'record:srv'
NIOS_NAPTR_RECORD = 'record:naptr'
NIOS_TXT_RECORD = 'record:txt'
NIOS_NSGROUP = 'nsgroup'
NIOS_IPV4_FIXED_ADDRESS = 'fixedaddress'
NIOS_IPV6_FIXED_ADDRESS = 'ipv6fixedaddress'
NIOS_NEXT_AVAILABLE_IP = 'func:nextavailableip'
NIOS_IPV4_NETWORK_CONTAINER = 'networkcontainer'
NIOS_IPV6_NETWORK_CONTAINER = 'ipv6networkcontainer'
NIOS_MEMBER = 'member'
NIOS_DTC_SERVER = 'dtc:server'
NIOS_DTC_POOL = 'dtc:pool'
NIOS_DTC_LBDN = 'dtc:lbdn'
NIOS_NSGROUP_FORWARDSTUBSERVER = 'nsgroup:forwardstubserver'
NIOS_NSGROUP_FORWARDINGMEMBER = 'nsgroup:forwardingmember'
NIOS_NSGROUP_DELEGATION = 'nsgroup:delegation'
NIOS_NSGROUP_STUBMEMBER = 'nsgroup:stubmember'
NIOS_DTC_MONITOR_HTTP = 'dtc:monitor:http'
NIOS_DTC_MONITOR_ICMP = 'dtc:monitor:icmp'
NIOS_DTC_MONITOR_PDP = 'dtc:monitor:pdp'
NIOS_DTC_MONITOR_SIP = 'dtc:monitor:sip'
NIOS_DTC_MONITOR_SNMP = 'dtc:monitor:snmp'
NIOS_DTC_MONITOR_TCP = 'dtc:monitor:tcp'
NIOS_DTC_TOPOLOGY = 'dtc:topology'
NIOS_EXTENSIBLE_ATTRIBUTE = 'extensibleattributedef'
NIOS_VLAN = 'vlan'
NIOS_ADMINUSER = 'adminuser'

NIOS_PROVIDER_SPEC = {
    'host': dict(fallback=(env_fallback, ['INFOBLOX_HOST'])),
    'username': dict(fallback=(env_fallback, ['INFOBLOX_USERNAME'])),
    'password': dict(fallback=(env_fallback, ['INFOBLOX_PASSWORD']), no_log=True),
    'cert': dict(fallback=(env_fallback, ['INFOBLOX_CERT'])),
    'key': dict(fallback=(env_fallback, ['INFOBLOX_KEY']), no_log=True),
    'validate_certs': dict(type='bool', default=False, fallback=(env_fallback, ['INFOBLOX_SSL_VERIFY']),
                           aliases=['ssl_verify']),
    'silent_ssl_warnings': dict(type='bool', default=True),
    'http_request_timeout': dict(type='int', default=10, fallback=(env_fallback, ['INFOBLOX_HTTP_REQUEST_TIMEOUT'])),
    'http_pool_connections': dict(type='int', default=10),
    'http_pool_maxsize': dict(type='int', default=10),
    'max_retries': dict(type='int', default=3, fallback=(env_fallback, ['INFOBLOX_MAX_RETRIES'])),
    'wapi_version': dict(default='2.12.3', fallback=(env_fallback, ['INFOBLOX_WAPI_VERSION'])),
    'max_results': dict(type='int', default=1000, fallback=(env_fallback, ['INFOBLOX_MAX_RESULTS']))
}


def _safe_parse_bool(value):
    """Safely parse a boolean from string without using eval()."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lower = value.lower().strip()
        if lower in ('true', '1', 'yes'):
            return True
        if lower in ('false', '0', 'no'):
            return False
    raise ValueError("Cannot parse '%s' as boolean" % value)


def _safe_parse_int(value):
    """Safely parse an integer from string without using eval()."""
    return int(value)


def get_connector(*args, **kwargs):
    """Returns an instance of infoblox_client.connector.Connector.

    :params args: positional arguments are silently ignored
    :params kwargs: dict that is passed to Connector init
    :returns: Connector
    """
    if not HAS_INFOBLOX_CLIENT:
        raise Exception('infoblox-client is required but does not appear '
                        'to be installed.  It can be installed using the '
                        'command `pip install infoblox-client`')

    if not set(kwargs.keys()).issubset(list(NIOS_PROVIDER_SPEC.keys()) + ['ssl_verify']):
        raise Exception('invalid or unsupported keyword argument for connector')

    for key, value in NIOS_PROVIDER_SPEC.items():
        if key not in kwargs:
            # Apply default values from NIOS_PROVIDER_SPEC
            if 'default' in value:
                kwargs[key] = value['default']

            # Override with env variables unless explicitly set
            env = ('INFOBLOX_%s' % key).upper()
            if env in os.environ:
                if NIOS_PROVIDER_SPEC[key].get('type') == 'bool':
                    kwargs[key] = _safe_parse_bool(os.environ.get(env))
                elif NIOS_PROVIDER_SPEC[key].get('type') == 'int':
                    kwargs[key] = _safe_parse_int(os.environ.get(env))
                else:
                    kwargs[key] = os.environ.get(env)

    if 'validate_certs' in kwargs.keys():
        kwargs['ssl_verify'] = kwargs['validate_certs']
        kwargs.pop('validate_certs', None)

    return Connector(kwargs)
