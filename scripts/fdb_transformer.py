#!/usr/bin/env python
# 1) Convert dynamic FDB entries to static before warm reboot to avoid flooding
#     Usage: ./fdb_dyn_to_static.py --pre_reboot
# 2) Convert static FDB entries to dynamic after warm reboot
#     Usage: ./fdb_dyn_to_static.py --post_reboot
# Heavily Borrowed from fast-reboot-dump.py

import time
import json
import argparse
import sys
from swsscommon import swsscommon
from sonic_py_common import logger

log = logger.Logger("FDB Transformer")

TRANSFORMED_FIELD = "transformed" # used for dynamic->static conversion post reboot

def is_mac_unicast(mac):
    first_octet = mac.split(':')[0]
    return int(first_octet, 16) & 0x01 == 0

def get_vlan_ifaces():
    vlans = []
    with open('/proc/net/dev') as fp:
        vlans = [line.split(':')[0].strip() for line in fp if 'Vlan' in line]

    return vlans

def get_bridge_port_id_2_port_id(db):
    bridge_port_id_2_port_id = {}
    keys = db.keys(db.ASIC_DB, 'ASIC_STATE:SAI_OBJECT_TYPE_BRIDGE_PORT:oid:*')
    keys = [] if keys is None else keys
    for key in keys:
        value = db.get_all(db.ASIC_DB, key)
        port_type = value['SAI_BRIDGE_PORT_ATTR_TYPE']
        if port_type != 'SAI_BRIDGE_PORT_TYPE_PORT':
            continue
        port_id = value['SAI_BRIDGE_PORT_ATTR_PORT_ID']
        # ignore admin status
        bridge_id = key.replace('ASIC_STATE:SAI_OBJECT_TYPE_BRIDGE_PORT:', '')
        bridge_port_id_2_port_id[bridge_id] = port_id

    return bridge_port_id_2_port_id

def get_lag_by_member(member_name, app_db):
    keys = app_db.keys(app_db.APPL_DB, 'LAG_MEMBER_TABLE:*')
    keys = [] if keys is None else keys
    for key in keys:
        _, lag_name, lag_member_name = key.split(":")
        if lag_member_name == member_name:
            return lag_name
    return None

def get_map_host_port_id_2_iface_name(asic_db):
    host_port_id_2_iface = {}
    keys = asic_db.keys(asic_db.ASIC_DB, 'ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF:oid:*')
    keys = [] if keys is None else keys
    for key in keys:
        value = asic_db.get_all(asic_db.ASIC_DB, key)
        if value['SAI_HOSTIF_ATTR_TYPE'] != 'SAI_HOSTIF_TYPE_NETDEV':
            continue
        port_id = value['SAI_HOSTIF_ATTR_OBJ_ID']
        iface_name = value['SAI_HOSTIF_ATTR_NAME']
        host_port_id_2_iface[port_id] = iface_name

    return host_port_id_2_iface

def get_map_lag_port_id_2_portchannel_name(asic_db, app_db, host_port_id_2_iface):
    lag_port_id_2_iface = {}
    keys = asic_db.keys(asic_db.ASIC_DB, 'ASIC_STATE:SAI_OBJECT_TYPE_LAG_MEMBER:oid:*')
    keys = [] if keys is None else keys
    for key in keys:
        value = asic_db.get_all(asic_db.ASIC_DB, key)
        lag_id = value['SAI_LAG_MEMBER_ATTR_LAG_ID']
        if lag_id in lag_port_id_2_iface:
            continue
        member_id = value['SAI_LAG_MEMBER_ATTR_PORT_ID']
        member_name = host_port_id_2_iface[member_id]
        lag_name = get_lag_by_member(member_name, app_db)
        if lag_name is not None:
            lag_port_id_2_iface[lag_id] = lag_name

    return lag_port_id_2_iface

def get_map_port_id_2_iface_name(asic_db, app_db):
    port_id_2_iface = {}
    host_port_id_2_iface = get_map_host_port_id_2_iface_name(asic_db)
    port_id_2_iface.update(host_port_id_2_iface)
    lag_port_id_2_iface = get_map_lag_port_id_2_portchannel_name(asic_db, app_db, host_port_id_2_iface)
    port_id_2_iface.update(lag_port_id_2_iface)

    return port_id_2_iface

def get_map_bridge_port_id_2_iface_name(asic_db, app_db):
    bridge_port_id_2_port_id = get_bridge_port_id_2_port_id(asic_db)
    port_id_2_iface = get_map_port_id_2_iface_name(asic_db, app_db)

    bridge_port_id_2_iface_name = {}

    for bridge_port_id, port_id in bridge_port_id_2_port_id.items():
        if port_id in port_id_2_iface:
            bridge_port_id_2_iface_name[bridge_port_id] = port_id_2_iface[port_id]
        else:
            print("Not found")

    return bridge_port_id_2_iface_name

def get_vlan_oid_by_vlan_id(db, vlan_id):
    keys = db.keys(db.ASIC_DB, 'ASIC_STATE:SAI_OBJECT_TYPE_VLAN:oid:*')
    keys = [] if keys is None else keys
    for key in keys:
        value = db.get_all(db.ASIC_DB, key)
        if 'SAI_VLAN_ATTR_VLAN_ID' in value and int(value['SAI_VLAN_ATTR_VLAN_ID']) == vlan_id:
            return key.replace('ASIC_STATE:SAI_OBJECT_TYPE_VLAN:', '')

    raise Exception('Not found bvi oid for vlan_id: %d' % vlan_id)

def convert_static_to_dynamic_using_asic(dry_run=False):
    asic_db = swsscommon.SonicV2Connector(use_unix_socket_path=False)
    app_db = swsscommon.SonicV2Connector(use_unix_socket_path=False)
    asic_db.connect(asic_db.ASIC_DB, False)
    app_db.connect(app_db.APPL_DB, False)
    db_appl = swsscommon.DBConnector("APPL_DB", 0, False)
    pipeline = swsscommon.RedisPipeline(db_appl)
    fdb_producer = swsscommon.ProducerStateTable(pipeline, "FDB_TABLE", True)
    fdb_table = swsscommon.Table(db_appl, "FDB_TABLE")

    bridge_id_2_iface = get_map_bridge_port_id_2_iface_name(asic_db, app_db)
    vlan_ifaces = get_vlan_ifaces()
    all_dynamic_fdb_keys = {}

    for vlan in vlan_ifaces:
        vlan_id = int(vlan.replace('Vlan', ''))
        bvid = get_vlan_oid_by_vlan_id(asic_db, vlan_id)
        fdb_keys = asic_db.keys(asic_db.ASIC_DB, 'ASIC_STATE:SAI_OBJECT_TYPE_FDB_ENTRY:{*\"bvid\":\"%s\"*}' % bvid)
        # Process each FDB entry
        for key in fdb_keys:
            fdb_entry = asic_db.get_all(asic_db.ASIC_DB, key)
            if not fdb_entry:
                continue

            # Only process dynamic entries
            if fdb_entry.get("SAI_FDB_ENTRY_ATTR_TYPE") != "SAI_FDB_ENTRY_TYPE_DYNAMIC":
                continue

            # Extract MAC and VLAN info from the key
            key_data = json.loads(key.split(":", 2)[2])
            mac = key_data.get("mac", "").replace(":", "-")

            if not mac:
                continue

            # Get port information
            bridge_port_oid = fdb_entry.get("SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID")
            if not bridge_port_oid:
                continue

            port_name = bridge_id_2_iface.get(bridge_port_oid)
            if not port_name:
                continue

            if dry_run:
                print(f"Converted FDB entry {vlan}:{mac}:{port_name} to static")
            else:
                field_values = []
                field_values.append(("type", "static"))
                field_values.append(("port", port_name))
                field_values.append((TRANSFORMED_FIELD, "true"))
                fdb_producer.set(f"{vlan}:{mac}", field_values)
                log.log_notice(f"Convert FDB entry {vlan}:{mac}:{port_name} to static")

            all_dynamic_fdb_keys[f"{vlan}:{mac}"] = key

    if not dry_run:
        pipeline.flush()

    # Wait until all dynamic FDB entries are converted to static in ASIC DB
    # for appl_key, key in all_dynamic_fdb_keys.items():
    #     fdb_entry = asic_db.get_all(asic_db.ASIC_DB, key)
    #     if not dry_run:
    #         tries = 50
    #     else:
    #         tries = 1

    #     while fdb_entry and fdb_entry.get("SAI_FDB_ENTRY_ATTR_TYPE") != "SAI_FDB_ENTRY_TYPE_STATIC":
    #         time.sleep(0.1)
    #         tries = tries - 1
    #         if tries == 0:
    #             break
    #         fdb_entry = asic_db.get_all(asic_db.ASIC_DB, key)
    
    #     if fdb_entry and fdb_entry.get("SAI_FDB_ENTRY_ATTR_TYPE") == "SAI_FDB_ENTRY_TYPE_DYNAMIC":
    #         log.log_info(f"FDB entry fdb_entry: {key} converted to static")

def convert_dynamic_to_static(dry_run=False):
    app_db = swsscommon.SonicV2Connector(use_unix_socket_path=False)
    app_db.connect(app_db.APPL_DB, False)
    db_appl = swsscommon.DBConnector("APPL_DB", 0, False)
    pipeline = swsscommon.RedisPipeline(db_appl)
    fdb_producer = swsscommon.ProducerStateTable(pipeline, "FDB_TABLE", True)
    fdb_table = swsscommon.Table(db_appl, "FDB_TABLE")

    # Get all FDB entries from APPL_DB
    keys = app_db.keys(app_db.APPL_DB, "FDB_TABLE:*")
    keys = [] if keys is None else keys

    for key in keys:
        entry = app_db.get_all(app_db.APPL_DB, key)
        if entry.get(TRANSFORMED_FIELD) == "true":
            if dry_run:
                print(f"Converting FDB entry {key} back to dynamic")
            else:
                field_values = []
                field_values.append(("type", "dynamic"))
                field_values.append(("port", entry["port"]))
                fdb_producer.set(key.replace("FDB_TABLE:", ""), field_values)
                log.log_notice(f"Convert FDB entry {key} back to dynamic")

    if not dry_run:
        pipeline.flush()
    

parser = argparse.ArgumentParser(description='Convert FDB entries to static->dynamic before warm reboot or dynamic->static after warm reboot')
parser.add_argument('--dry_run', action='store_true', default=False, help='Dry run the script and print the dynamic FDB entries')
optional = parser._action_groups.pop()
group1 = parser.add_argument_group("Required arguments")
group1.add_argument('--pre_reboot', action='store_true', default=False, help='Perform the conversion before warm reboot')
group1.add_argument('--post_reboot', action='store_true', default=False, help='Perform the conversion after warm reboot')
parser._action_groups.append(optional) # add optional arguments section again
args = parser.parse_args()

if args.pre_reboot:
    convert_static_to_dynamic_using_asic(args.dry_run)
else:
    convert_dynamic_to_static(args.dry_run)