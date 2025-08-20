from tkinter import NO
from src.rpc import RPCClient
from src.config import FibersConfig

def shutdown_check(config):
    fibers_config = FibersConfig(config)

    ckbClient = RPCClient(config.get("ckb").get("url"))
    # txs = get_ln_tx_trace(ckbClient,"0x07caa2ec6678720ddc11986c34be172a5b0ec7e3c357d79234831aa8eda045b1")
    # for tx in txs:
        # print(tx)
    for key in fibers_config.fibersMap.keys():
        fiber = fibers_config.fibersMap[key]
        print(f"current key:{key}")
        try:
            list_channels = fiber.list_channels({"include_closed": True})
        except:
            print(f"current key:{key} list_channels error")
            continue
        traces = []
        
        # fiber_arg = fiber.node_info()["default_funding_lock_script"][
            # "args"
        # ]
        fee = 455
        for channel in list_channels["channels"]:
            if channel["state"]['state_name'] == "CLOSED" or channel["state"]['state_name'] == "SHUTTING_DOWN":
                try:
            #  {
                # "state_name": "CLOSED",
                # "state_flags": "UNCOOPERATIVE",
            # }:
                # continue
                    trace = get_ln_tx_trace(ckbClient,channel["channel_outpoint"][:-8])
                    traces.append({"channel_id": channel["channel_id"], "trace": trace})
                    for tx in trace:
                        if tx['tx_hash'] == None:
                            continue
                        # print("tx:",tx)
                        print("key",key,'channel id:', channel["channel_id"]," tx_hash:",tx['tx_hash'],"fee:",tx['msg']['fee'],"udt_fee:",tx['msg']['udt_fee'])
                except:
                    print(f"current key:{key} get_ln_tx_trace error")
                    continue
            # fiber1_balance = int(channel["remote_balance"], 16)
            # fiber_balance = (
            #     int(channel["local_balance"], 16)
            #     - int(channel["offered_tlc_balance"], 16)
            #     + int(channel["received_tlc_balance"], 16)
            # )
            # depositBalance = 6200000000 if channel['funding_udt_type_script'] == None else 0
            # fee = 455 if channel['funding_udt_type_script'] == None else 0
            # assert {
            #     "args": fiber1_arg,
            #     "capacity": fiber1_balance - fee + depositBalance,
            # } in trace[-2]["msg"]["output_cells"],f"current key:{key},channel message:{channel}"
            # assert {
                # "args": fiber_arg,
                # "capacity": fiber_balance - fee + depositBalance,
            # } in trace[-2]["msg"]["output_cells"],f"current key:{key},channel message:{channel}"
           




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
        return []
    tx = ckbClient.get_transaction(tx_hash)
    input_cells = []
    output_cells = []

    # self.node.getClient().get_transaction(tx['transaction']['inputs'][])
    for i in range(len(tx["transaction"]["inputs"])):
        pre_cell = ckbClient.get_transaction(
            tx["transaction"]["inputs"][i]["previous_output"]["tx_hash"]
        )["transaction"]["outputs"][
            int(tx["transaction"]["inputs"][i]["previous_output"]["index"], 16)
        ]
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
        'udt_fee':udt_fee
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
