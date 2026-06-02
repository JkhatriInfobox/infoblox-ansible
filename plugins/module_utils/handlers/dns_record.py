from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from .base import BaseObjectHandler


class DnsRecordHandler(BaseObjectHandler):
    """Handler for DNS record types that share common behavior.

    Used for: record:aaaa, record:ptr, record:srv, record:naptr
    These records all need 'view' removed before update.
    """

    def pre_update(self, wapi, ref, proposed_object, current_object, ib_spec, module):
        """Remove 'view' before update (not supported for these record types)."""
        proposed_object = self.on_update(proposed_object, ib_spec)
        proposed_object.pop('view', None)
        return ref, proposed_object
