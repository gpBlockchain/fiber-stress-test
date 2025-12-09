from src.rpc import RPCClient
from src.config import FibersConfig
import datetime
import hashlib

def check_shutdown_msg(config):
    fibers_config = FibersConfig(config)
    for fiber_key in fibers_config.fibersMap.keys():
        print(f"current key: {fiber_key}")
        try:
            fiber = fibers_config.fibersMap[fiber_key]
            ckbClient = RPCClient(config.get("ckb").get("url"))
            
            # 获取强制shutdown的channel 
            channels = fiber.list_channels({"include_closed":True})
            # 获取shutdown交易列表
            force_shutdown_channel_messages = {}
            for channel in channels['channels']:
                # print(channel)
                if channel['state'].get('state_flags',"").startswith("UNCOOPERATIVE"):
                    # print(f"channel_id: {channel['channel_id']}, channel_outpoint tx: {channel['channel_outpoint']}")
                    tx_trace = get_ln_tx_trace(ckbClient,channel['channel_outpoint'][:-8])
                    force_shutdown_channel_messages[channel['channel_id']] = {
                        "pending_tlcs": channel['pending_tlcs'],
                        "shutdown_txs": tx_trace
                    }
                    for tx in tx_trace:
                        print(tx)
            # print("force_shutdown_channel_messages:",force_shutdown_channel_messages)
            # 检查是否有对方通过preimage获取的交易
            unlocked_payment_hashes = set()
            pre_image_unlock_message_maps = {}
            for channel_id, data in force_shutdown_channel_messages.items():
                for tx_entry in data["shutdown_txs"]:
                    msg = tx_entry.get("msg", {})
                    if msg == None:
                        continue
                    witness = msg.get("witness",None)
                    
                    if not witness:
                        continue
                        
                    # witness structure: {'settlement': {'unlocks': [...]}} or {'revocation': ...}
                    if "settlement" in witness:
                        for unlock in witness["settlement"]["unlocks"]:
                            if unlock.get("with_preimage") == 1 and unlock.get("preimage") != "N/A":
                                preimage = unlock["preimage"]
                                ckb_payment_hash = ckb_hash(preimage)
                                sha256_payment_hash=  sha256(preimage)
                                for tlc in data['pending_tlcs']:
                                    if tlc['payment_hash'] == ckb_payment_hash or tlc['payment_hash'] == sha256_payment_hash:
                                        payment_hash = tlc['payment_hash']
                                        break
                                unlocked_payment_hashes.add(payment_hash)
                                print(f"Found preimage unlock: {preimage} -> {payment_hash} in channel {channel_id}")
                                if pre_image_unlock_message_maps.get(payment_hash) == None:
                                    pre_image_unlock_message_maps[payment_hash]= []
                                pre_image_unlock_message_maps[payment_hash].append({
                                    "channel_id": channel_id,
                                    "preimage": preimage,
                                    "settle_tx_hash":tx_entry['tx_hash']
                                })
            for channel in channels['channels']:
                for tlc in channel['pending_tlcs']:
                    if tlc['payment_hash'] in pre_image_unlock_message_maps.keys():
                        is_new = False
                        # print(f"Found pending tlc: {tlc} in channel {channel_id}")
                        for i in  range(len(pre_image_unlock_message_maps[tlc['payment_hash']])):
                            if pre_image_unlock_message_maps[tlc['payment_hash']][i]['channel_id'] == channel['channel_id']:
                                pre_image_unlock_message_maps[tlc['payment_hash']][i]['tlc'] = tlc
                                is_new = True
                        if is_new != True:
                            pre_image_unlock_message_maps[tlc['payment_hash']].append({
                                "channel_id": channel['channel_id'],
                                "tlc": tlc
                            })
            
            for payment_hash, messages in pre_image_unlock_message_maps.items():
                # comment: 检查是否有tlc在其他channel中被解锁
                print(f"[{fiber_key}] payment_hash: {payment_hash}, messages: {messages}")
                if len(messages) ==2:
                    # 如果有2个，2个肯定都有settle_tx_hash
                    if messages[0].get("settle_tx_hash",None) == None or messages[1].get("settle_tx_hash",None) == None:
                        print(f"Error {fiber_key} payment_hash: {payment_hash}, messages: {messages}")                
        except Exception as e:
            print(f"Error key: {fiber_key} :{e}")
 
    
    


def ckb_hasher():
    return hashlib.blake2b(digest_size=32, person=b"ckb-default-hash")


def ckb_hash(message):
    hasher = ckb_hasher()
    hasher.update(bytes.fromhex(message.replace("0x", "")))
    return "0x" + hasher.hexdigest()


def get_ln_tx_trace(ckbClient,open_channel_tx_hash):
    tx_trace = []
    tx_trace.append(
        {
            "tx_hash": open_channel_tx_hash,
            "msg": get_tx_message(ckbClient,open_channel_tx_hash),
        }
    )
    tx, code_hash = get_ln_cell_death_hash(ckbClient,open_channel_tx_hash)
    tx_trace.append({"tx_hash": tx, "msg": get_tx_message(ckbClient,tx)})
    while tx is not None:
        tx, new_code_hash = get_ln_cell_death_hash(ckbClient,tx)
        tx_trace.append({"tx_hash": tx, "msg": get_tx_message(ckbClient,tx)})
        if (
            new_code_hash
            != "0x740dee83f87c6f309824d8fd3fbdd3c8380ee6fc9acc90b1a748438afcdf81d8"
        ):
            # print("code_hash changed, stop trace")
            # print("old code_hash:", code_hash, "new code_hash:", new_code_hash)
            tx = None
    # for i in range(len(tx_trace)):
        # print(tx_trace[i])
    return tx_trace

def get_ln_cell_death_hash(ckbClient,tx_hash):
    tx = ckbClient.get_transaction(tx_hash)
    cellLock = tx["transaction"]["outputs"][0]["lock"]

    txs = ckbClient.get_transactions(
        {
            "script": cellLock,
            "script_type": "lock",
            "script_search_mode": "exact",
        },
        "asc",
        "0xff",
        None,
    )
    if len(txs["objects"]) == 2:
        return txs["objects"][1]["tx_hash"], cellLock["code_hash"]
    return None, None

def get_tx_message(ckbClient, tx_hash):
    if tx_hash is None:
        return None
    tx = ckbClient.get_transaction(tx_hash)
    input_cells = []
    output_cells = []
    is_commit_lock = False
    # self.node.getClient().get_transaction(tx['transaction']['inputs'][])
    for i in range(len(tx["transaction"]["inputs"])):
        pre_cell = ckbClient.get_transaction(
            tx["transaction"]["inputs"][i]["previous_output"]["tx_hash"]
        )["transaction"]["outputs"][
            int(tx["transaction"]["inputs"][i]["previous_output"]["index"], 16)
        ]
        # check input contains commit_lock:0x740dee83f87c6f309824d8fd3fbdd3c8380ee6fc9acc90b1a748438afcdf81d8
        if pre_cell["lock"]["code_hash"] == "0x740dee83f87c6f309824d8fd3fbdd3c8380ee6fc9acc90b1a748438afcdf81d8":
            is_commit_lock = True
        pre_cell_outputs_data = ckbClient.get_transaction(
            tx["transaction"]["inputs"][i]["previous_output"]["tx_hash"]
        )["transaction"]["outputs_data"][
            int(tx["transaction"]["inputs"][i]["previous_output"]["index"], 16)
        ]
        if pre_cell["type"] is None:
            input_cells.append(
                {
                    "args": pre_cell["lock"]["args"],
                    "capacity": int(pre_cell["capacity"], 16),
                }
            )
            continue
        input_cells.append(
            {
                "args": pre_cell["lock"]["args"],
                "capacity": int(pre_cell["capacity"], 16),
                "udt_args": pre_cell["type"]["args"],
                "udt_capacity": to_int_from_big_uint128_le(pre_cell_outputs_data),
            }
        )

    for i in range(len(tx["transaction"]["outputs"])):
        if tx["transaction"]["outputs"][i]["type"] is None:
            output_cells.append(
                {
                    "args": tx["transaction"]["outputs"][i]["lock"]["args"],
                    "capacity": int(
                        tx["transaction"]["outputs"][i]["capacity"], 16
                    ),
                }
            )
            continue
        output_cells.append(
            {
                "args": tx["transaction"]["outputs"][i]["lock"]["args"],
                "capacity": int(tx["transaction"]["outputs"][i]["capacity"], 16),
                "udt_args": tx["transaction"]["outputs"][i]["type"]["args"],
                "udt_capacity": to_int_from_big_uint128_le(
                    tx["transaction"]["outputs_data"][i]
                ),
            }
        )
    # print({"input_cells": input_cells, "output_cells": output_cells})
    input_cap = 0
    for i in range(len(input_cells)):
        input_cap = input_cap + input_cells[i]["capacity"]
    for i in range(len(output_cells)):
        input_cap = input_cap - output_cells[i]["capacity"]
    udt_fee = 0
    for i in range(len(input_cells)):
        if 'udt_args' in input_cells[i]:
            udt_fee = udt_fee + input_cells[i]['udt_capacity']
    for i in range(len(output_cells)):
        if 'udt_args' in output_cells[i]:
            udt_fee = udt_fee - output_cells[i]['udt_capacity']
    return {
        "input_cells": input_cells,
        "output_cells": output_cells,
        "fee": input_cap,
        'udt_fee':udt_fee,
        "witness": parse_witness_v2(tx["transaction"]["witnesses"][0]) if is_commit_lock else None,
    }

def to_int_from_big_uint128_le(hex_str):
    # Strip the '0x' prefix if present
    if hex_str.startswith("0x"):
        hex_str = hex_str[2:]

    # Convert the hex string into a byte array (16 bytes for uint128)
    buf = bytearray.fromhex(hex_str)

    # Reverse the byte array to convert from little-endian to big-endian
    buf.reverse()

    # Convert the byte array into an integer
    result = int.from_bytes(buf, byteorder="big")

    return result

def parse_witness_v2(hex_str):
    data = hex_str[2:] if hex_str.startswith('0x') else hex_str
    offset = 0

    empty_witness_args = data[offset : offset + 32]
    offset += 32

    unlock_count = int(data[offset : offset + 2], 16)
    offset += 2

    witness_data = {
        "empty_witness_args": f"0x{empty_witness_args}",
        "unlock_count": unlock_count,
    }

    if unlock_count == 0x00:  # Revocation unlock
        version_hex = data[offset : offset + 16]
        version = int(version_hex, 16)
        offset += 16

        pubkey = f"0x{data[offset : offset + 64]}"
        offset += 64

        signature = f"0x{data[offset:]}"

        witness_data["revocation"] = {
            "version": version,
            "pubkey": pubkey,
            "signature": signature,
        }
    else:  # Settlement unlock
        pending_htlc_count = int(data[offset : offset + 2], 16)
        offset += 2
        htlcs = []

        for i in range(pending_htlc_count):
            htlc_type = int(data[offset : offset + 2], 16)
            offset += 2

            payment_amount_hex = data[offset : offset + 32]
            payment_amount = int.from_bytes(bytes.fromhex(payment_amount_hex), 'little')
            offset += 32

            payment_hash = f"0x{data[offset : offset + 40]}"
            offset += 40

            remote_htlc_pubkey_hash = f"0x{data[offset : offset + 40]}"
            offset += 40

            local_htlc_pubkey_hash = f"0x{data[offset : offset + 40]}"
            offset += 40

            htlc_expiry_hex = data[offset : offset + 16]
            htlc_expiry_timestamp = int.from_bytes(bytes.fromhex(htlc_expiry_hex), 'little')

            htlc_expiry_timestamp = (htlc_expiry_timestamp & ((1 << 56) - 1)) * 1000
            
            dt = datetime.datetime.fromtimestamp(htlc_expiry_timestamp / 1000.0)
            htlc_expiry = dt.strftime('%Y/%m/%d %H:%M:%S')
            
            offset += 16

            htlc = {
                "htlc_type": htlc_type,
                "payment_amount": payment_amount,
                "payment_hash": payment_hash,
                "remote_htlc_pubkey_hash": remote_htlc_pubkey_hash,
                "local_htlc_pubkey_hash": local_htlc_pubkey_hash,
                "htlc_expiry": htlc_expiry,
                "htlc_expiry_timestamp": htlc_expiry_timestamp,
            }
            htlcs.append(htlc)

        settlement_remote_pubkey_hash = f"0x{data[offset : offset + 40]}"
        offset += 40
        
        settlement_remote_amount = int.from_bytes(bytes.fromhex(data[offset : offset + 32]), 'little')
        offset += 32
        
        settlement_local_pubkey_hash = f"0x{data[offset : offset + 40]}"
        offset += 40
        
        settlement_local_amount = int.from_bytes(bytes.fromhex(data[offset : offset + 32]), 'little')
        offset += 32

        unlocks = []
        for i in range(unlock_count):
            unlock_type = int(data[offset : offset + 2], 16)
            offset += 2
            
            with_preimage = int(data[offset : offset + 2], 16)
            offset += 2
            
            signature = f"0x{data[offset : offset + 130]}"
            offset += 130
            
            preimage = "N/A"
            if with_preimage == 0x01:
                preimage = f"0x{data[offset : offset + 64]}"
                offset += 64
            
            unlocks.append({
                "unlock_type": unlock_type,
                "with_preimage": with_preimage,
                "signature": signature,
                "preimage": preimage
            })

        witness_data["settlement"] = {
            "pending_htlc_count": pending_htlc_count,
            "htlcs": htlcs,
            "settlement_remote_pubkey_hash": settlement_remote_pubkey_hash,
            "settlement_remote_amount": settlement_remote_amount,
            "settlement_local_pubkey_hash": settlement_local_pubkey_hash,
            "settlement_local_amount": settlement_local_amount,
            "unlocks": unlocks,
        }

    return witness_data


def sha256(preimage_hex: str) -> str:
    raw = bytes.fromhex(preimage_hex.replace("0x", ""))
    return "0x" + hashlib.sha256(raw).hexdigest()
