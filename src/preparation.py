from concurrent.futures import ThreadPoolExecutor
import time
from src.config import FibersConfig
import logging

LOGGER = logging.getLogger(__name__)

ledger_channels = []

def connect_nodes(config):
    print("--- Running Preparation Phase: Connecting Nodes ---")
    fibers_config = FibersConfig(config)
    fiber_keys = fibers_config.fibersMap.keys()
    print("fiber_keys:",fiber_keys)
    graph_channels = fibers_config.fibersMap[list(fiber_keys)[0]].graph_channels({})
    for channel in graph_channels['channels']:
        ledger_channels.append({
            'node_1': channel['node1'],
            'node_2': channel['node2'],
            'capacity': int(channel['capacity'],16),
        })
    if 'connect_to' in config:
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = []
            for connection in config['connect_to']:
                targets = connection.get('targets', [])
                source_node = connection.get('id')
                capacitys = connection.get('capacitys', [])
                capacitys_sum = 0
                #  check capcitys len == targets len
                if len(capacitys) != len(targets):
                    raise Exception(f"capacitys len:{len(capacitys)} != targets len:{len(targets)}")
                #  check target id exist
                for target in targets:
                    if target not in fibers_config.fibersMap:
                        raise Exception(f"target id:{target} not exist")

                for i in range(len(capacitys)):
                    capacitys_sum += capacitys[i]
                print(f"fiber id:{connection.get('id')} need capacity:{capacitys_sum}")
                # todo check capacity enough
                # skip channel if cap in ledger_channels
                
                future = executor.submit(open_channel_by_id, fibers_config, source_node, targets, capacitys)
                futures.append(future)

            for future in futures:
                future.result()  # Wait for all tasks to complete

    print("--- Preparation Phase Complete ---")


def open_channel_by_id(fibers_config, source_node, targets, capacitys, udt=None):
    for i in range(len(targets)):
        target_node = targets[i]
        print(f"open channel from {source_node} to {target_node} with capacity {capacitys[i]}")
        # To prevent deadlock, always lock in the same order.
        lock1_id, lock2_id = sorted([source_node, target_node])
        lock1 = fibers_config.fiber_locks[lock1_id]
        lock2 = fibers_config.fiber_locks[lock2_id]

        lock1.acquire()
        lock2.acquire()
        try:
            open_channel(fibers_config.fibersMap[source_node], fibers_config.fibersMap[target_node], capacitys[i], udt)
            print(f"open channel from {source_node} to {target_node} with capacity {capacitys[i]} success")
        finally:
            lock2.release()
            lock1.release()


def open_channel(fiber1, fiber2, capacity,udt=None):
    """
    打开一个通道
    确认通道创建成功
    """
    if {'node_1': fiber1.node_info()['node_id'], 'node_2': fiber2.node_info()['node_id'], 'capacity': (capacity-62)*100000000} in ledger_channels:
        print("skip channel if cap in ledger_channels")
        return
    if {'node_1': fiber2.node_info()['node_id'], 'node_2': fiber1.node_info()['node_id'], 'capacity': (capacity-62)*100000000} in ledger_channels:
        print("skip channel if cap in ledger_channels in reverse")
        return
    fiber2_node_info = fiber2.node_info()
    fiber1.connect_peer({"address": fiber2_node_info["addresses"][0]})
    time.sleep(1)
    fiber2_peer_id = fiber2_node_info["addresses"][0].split("/")[-1]
    open_channel_config = {
        "peer_id": fiber2_peer_id,
        "funding_amount": hex(capacity*100000000),
        "tlc_fee_proportional_millionths": hex(1000),
        "public": True,
        "funding_udt_type_script": udt,
    }
    try:
        fiber1.open_channel(open_channel_config)
    except Exception as e:
        print(f"open channel failed:{e}")
    wait_for_channel_state(fiber1, fiber2_peer_id, "CHANNEL_READY")
    try:
        send_payment(fiber1,fiber2,int(capacity*100000000/2),udt=udt)
    except Exception as e:
        print(f"send payment failed:{e}")

def send_payment(fiber1, fiber2, amount, wait=True, udt=None, try_count=5):
    for i in range(try_count):
        try:
            payment = fiber1.send_payment(
                {
                    "target_pubkey": fiber2.node_info()["node_id"],
                    "amount": hex(amount),
                    "keysend": True,
                    "allow_self_payment": True,
                    "udt_type_script": udt,
                }
            )
            if wait:
                self.wait_payment_state(
                    fiber1, payment["payment_hash"], "Success", 600, 0.1
                )
            return payment["payment_hash"]
        except Exception as e:
            time.sleep(1)
            continue
    payment = fiber1.send_payment(
        {
            "target_pubkey": fiber2.node_info()["node_id"],
            "amount": hex(amount),
            "keysend": True,
            "allow_self_payment": True,
            "udt_type_script": udt,
        }
    )
    if wait:
        wait_payment_state(
            fiber1, payment["payment_hash"], "Success", 600, 0.1
        )
    return payment["payment_hash"]

def check_connect(config):
    print("--- Running Check Connect Phase: Verifying Channels ---")
    ledger_channels = []
    fibers_config = FibersConfig(config)
    fiber_keys = fibers_config.fibersMap.keys()
    print("fiber_keys:",fiber_keys)
    graph_channels = fibers_config.fibersMap[list(fiber_keys)[0]].graph_channels({})
    for channel in graph_channels['channels']:
        ledger_channels.append({
            'node_1': channel['node1'],
            'node_2': channel['node2'],
            'capacity': int(channel['capacity'],16),
        })

    if 'connect_to' in config:
        total_channels = 0
        for connection in config['connect_to']:
            total_channels += len(connection.get('targets', []))
        print(f"current channels:{len(ledger_channels)} expect channels:{total_channels}")
        not_exist_channels = []
        for connection in config['connect_to']:
            source_node_id = connection.get('id')
            targets = connection.get('targets', [])
            capacitys = connection.get('capacitys', [])
            source_rpc = fibers_config.fibersMap.get(source_node_id)
            
            for i in range(len(targets)):
                target_rpc = fibers_config.fibersMap.get(targets[i])
                if {'node_1': source_rpc.node_info()['node_id'], 'node_2': target_rpc.node_info()['node_id'], 'capacity': (capacitys[i]-62)*100000000} in ledger_channels:
                    print("skip channel if cap in ledger_channels")
                    continue
                if {'node_1': target_rpc.node_info()['node_id'], 'node_2': source_rpc.node_info()['node_id'], 'capacity': (capacitys[i]-62)*100000000} in ledger_channels:
                    print("skip channel if cap in ledger_channels in reverse")
                    continue
                print(f"Channel from {source_node_id} to {target_node_id} is not exist.")
                not_exist_channels.append({
                    'node_1': source_node_id,
                    'node_2': target_node_id,
                    'capacity': capacitys[i],
                })
                

    print("--- Check Connect Phase Complete ---")
    print(f"current channels:{len(ledger_channels)} expect channels:{total_channels}")
    print("----not exist channels -----")
    

def wait_payment_state(
     client, payment_hash, status="Success", timeout=360, interval=0.1
):
    for i in range(timeout):
        result = client.get_payment({"payment_hash": payment_hash})
        if result["status"] == status:
            return
        time.sleep(interval)
    raise TimeoutError(
        f"payment:{payment_hash} status did not reach state: {result['status']}, expected:{status} , within timeout period."
    )



def wait_for_channel_state(
    client,
    peer_id,
    expected_state,
    timeout=120,
    include_closed=False,
    channel_id=None,
):
    """Wait for a channel to reach a specific state.
    1. NEGOTIATING_FUNDING
    2. CHANNEL_READY
    3. CLOSED

    """
    for _ in range(timeout):
        channels = client.list_channels(
            {"peer_id": peer_id, "include_closed": include_closed}
        )
        if len(channels["channels"]) == 0:
            time.sleep(1)
            continue
        idx = 0
        if channel_id is not None:
            for i in range(len(channels["channels"])):
                print("channel_id:", channel_id)
                if channels["channels"][i]["channel_id"] == channel_id:
                    idx = i

        if channels["channels"][idx]["state"]["state_name"] == expected_state:
            LOGGER.info(f"Channel reached expected state: {expected_state}")
            # todo wait broading
            time.sleep(1)
            return channels["channels"][idx]["channel_id"]
        LOGGER.info(
            f"Waiting for channel state: {expected_state}, current state: {channels['channels'][0]['state']}"
        )
        time.sleep(1)
    raise TimeoutError(
        f"Channel did not reach state {expected_state} within timeout period."
    )


