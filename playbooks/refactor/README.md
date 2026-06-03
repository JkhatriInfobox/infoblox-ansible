# Refactor Matrix Playbooks

 delete) for all
`infoblox.nios_modules` modules and lookup plugins, validated against a real
NIOS grid (WAPI 2.13).

## Prerequisites

- NIOS grid reachable at the host configured in `group_vars/all.yml`
- Collection installed: `ansible-galaxy collection install infoblox-nios_modules-1.9.0.tar.gz --force`
- Python virtual env activated (`.venv/`)

## Configuration

Edit `group_vars/all.yml` to set your NIOS connection details:

```yaml
nios_provider:
  host: 172.28.82.65
  username: admin
  password: Infoblox@123
  wapi_version: "2.13"
  ssl_verify: false
grid_member: "infoblox.172_28_82_65"
```

## Running

### Module playbooks (no special env var needed)

```bash
cd playbooks/refactor
../../.venv/bin/ansible-playbook nios_zone_matrix.yml
```

### Lookup plugin playbooks (macOS only)

Lookup plugins use `requests`/`urllib3` inside Ansible worker forks. On macOS
with Python 3 this triggers the Objective-C runtime safety check and kills the
worker. Set the env var before running:

```bash
OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES ../../.venv/bin/ansible-playbook nios_lookup_matrix.yml
```

This applies to: `nios_lookup_matrix.yml`, `nios_next_ip_matrix.yml`,
`nios_next_network_matrix.yml`, `nios_next_vlan_id_matrix.yml`.

### Run all at once

```bash
OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES ../../.venv/bin/ansible-playbook \
  nios_zone_matrix.yml \
  nios_a_record_matrix.yml \
  nios_aaaa_record_matrix.yml \
  nios_cname_record_matrix.yml \
  nios_mx_record_matrix.yml \
  nios_srv_record_matrix.yml \
  nios_naptr_record_matrix.yml \
  nios_txt_record_matrix.yml \
  nios_ptr_record_matrix.yml \
  nios_host_record_matrix.yml \
  nios_dns_view_matrix.yml \
  nios_network_view_matrix.yml \
  nios_network_matrix.yml \
  nios_range_matrix.yml \
  nios_fixed_address_matrix.yml \
  nios_vlan_matrix.yml \
  nios_adminuser_matrix.yml \
  nios_extensible_attribute_matrix.yml \
  nios_member_matrix.yml \
  nios_restartservices_matrix.yml \
  nios_nsgroup_matrix.yml \
  nios_nsgroup_delegation_matrix.yml \
  nios_nsgroup_forwardingmember_matrix.yml \
  nios_nsgroup_forwardstubserver_matrix.yml \
  nios_nsgroup_stubmember_matrix.yml \
  nios_dtc_server_matrix.yml \
  nios_dtc_pool_matrix.yml \
  nios_dtc_monitor_http_matrix.yml \
  nios_dtc_monitor_icmp_matrix.yml \
  nios_dtc_monitor_sip_matrix.yml \
  nios_dtc_monitor_snmp_matrix.yml \
  nios_dtc_monitor_pdp_matrix.yml \
  nios_dtc_monitor_tcp_matrix.yml \
  nios_dtc_lbdn_matrix.yml \
  nios_dtc_topology_matrix.yml \
  nios_lookup_matrix.yml \
  nios_next_ip_matrix.yml \
  nios_next_network_matrix.yml \
  nios_next_vlan_id_matrix.yml
```

## Known Limitations

- **`nios_dtc_topology`**: WAPI 2.13 rejects `destination_link` in topology
  rules at the IBAP layer despite it appearing in the schema. Only
  name/comment lifecycle is tested.
- **`nios_member`**: SAFE  only `comment` is updated on the existingcontract 
  grid master. No rename, VIP change, or delete (would break the test grid).
- **macOS lookup crash**: Set `OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES` for
  any playbook using lookup plugins (see above).
