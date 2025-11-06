from concurrent.futures import ThreadPoolExecutor
from src.config import FibersConfig
from src.fiber_rpc import CKB_UNIT
from src.fiber_rpc import open_channel
import logging
from datetime import datetime, timedelta

LOGGER = logging.getLogger(__name__)

ledger_channels = []

def _parse_ts_to_dt(ts):
    """将可能为十六进制/十进制字符串或数值的时间戳解析为 datetime。
    - 支持形如 0x... 的十六进制时间戳
    - 支持秒或毫秒（数值大于 1e11 认为是毫秒）
    返回值：datetime 或 None
    """
    if ts is None:
        return None
    try:
        if isinstance(ts, str):
            if ts.lower().startswith('0x'):
                val = int(ts, 16)
            else:
                val = int(ts)
        elif isinstance(ts, (int, float)):
            val = int(ts)
        else:
            return None

        # 毫秒/秒判断
        if val > 10**11:
            val = val / 1000

        return datetime.fromtimestamp(val)
    except Exception:
        return None

def connect_nodes(config):
    print("--- Running Preparation Phase: Connecting Nodes ---")
    fibers_config = FibersConfig(config)
    fiber_keys = fibers_config.fibersMap.keys()
    graph_channels = fibers_config.fibersMap[list(fiber_keys)[0]].graph_channels({"limit":"0xfffff"})
    now = datetime.now()
    for channel in graph_channels['channels']:
        created = channel.get('created_timestamp')
        ts1 = (channel.get('update_info_of_node1') or {}).get('timestamp')
        ts2 = (channel.get('update_info_of_node2') or {}).get('timestamp')
        # 比较当前时间和 ts1/ts2/created，超过2天就跳过（ts1/ts2 可能为 hex）
        created_dt = _parse_ts_to_dt(created)
        ts1_dt = _parse_ts_to_dt(ts1)
        ts2_dt = _parse_ts_to_dt(ts2)
        candidates = [dt for dt in [created_dt, ts1_dt, ts2_dt] if dt is not None]
        latest_dt = max(candidates) if candidates else None
        if latest_dt is not None and (now - latest_dt) > timedelta(days=2):
            LOGGER.info(f"skip stale channel: outpoint={channel.get('channel_outpoint')} latest={latest_dt}")
            continue
        ledger_channels.append({
            'node_1': channel['node1'],
            'node_2': channel['node2'],
            'capacity': int(channel['capacity'],16),
            'udt_type_script': channel['udt_type_script'],
        })
    print(f"total {len(ledger_channels)} channels")
    if 'connect_to' in config:
        with ThreadPoolExecutor(max_workers=200) as executor:
            futures = []
            for connection in config['connect_to']:
                targets = connection.get('targets', [])
                source_node = connection.get('id')
                capacitys = connection.get('capacitys', [])
                udt = connection.get('udt', None)
                #  check capcitys len == targets len
                if len(capacitys) != len(targets):
                    raise Exception(f"capacitys len:{len(capacitys)} != targets len:{len(targets)}")
                #  check target id exist
                for target in targets:
                    if target not in fibers_config.fibersMap:
                        raise Exception(f"target id:{target} not exist")

                for i in range(len(targets)):
                    future = executor.submit(open_single_channel, fibers_config, source_node, targets[i], capacitys[i], udt)
                    futures.append(future)

            for future in futures:
                future.result()  # Wait for all tasks to complete

    print("--- Preparation Phase Complete ---")


def open_single_channel(fibers_config, source_node, target_node, capacity, udt=None):    # To prevent deadlock, always lock in the same order.
    lock1_id, lock2_id = sorted([source_node, target_node])
    lock1 = fibers_config.fiber_locks[lock1_id]
    lock2 = fibers_config.fiber_locks[lock2_id]
    lock1.acquire()
    lock2.acquire()
    print(f"acquire lock {lock1_id} and {lock2_id}")
    print(f"open channel from {source_node} to {target_node} with capacity {capacity}")
    try:
        graph_capacity = capacity * CKB_UNIT
        if udt is None:
            graph_capacity = graph_capacity - 62 * 100000000
        info = fibers_config.fibersMap[source_node].node_info()
        source_node_id = fibers_config.fibersMap[source_node].node_info()['node_id']
        target_node_id = fibers_config.fibersMap[target_node].node_info()['node_id']
        

        channel1 = {'node_1': source_node_id, 'node_2': target_node_id, 'capacity': graph_capacity,
                    'udt_type_script': udt}
        channel2 = {'node_1': target_node_id, 'node_2': source_node_id, 'capacity': graph_capacity,
                    'udt_type_script': udt}

        channel_exists = channel1 in ledger_channels or channel2 in ledger_channels
        if not channel_exists:
            open_channel(fibers_config.fibersMap[source_node], fibers_config.fibersMap[target_node], capacity,
                         udt)
            print(f"open channel from {source_node} to {target_node} with capacity {capacity} success")
        else:
            print("skip channel as it already exists in ledger")

    finally:
        lock2.release()
        lock1.release()
        print(f"release lock {lock1_id} and {lock2_id}")


def check_connect(config):
    print("--- Running Check Connect Phase: Verifying Channels ---")
    ledger_channels = []
    fibers_config = FibersConfig(config)
    fiber_keys = fibers_config.fibersMap.keys()
    graph_channels = fibers_config.fibersMap[list(fiber_keys)[0]].graph_channels({"limit":"0xfffff"})
    for channel in graph_channels['channels']:
        ledger_channels.append({
            'node_1': channel['node1'],
            'node_2': channel['node2'],
            'capacity': int(channel['capacity'],16),
            'udt_type_script':channel['udt_type_script'],
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
            udt = connection.get('udt',None)
            for i in range(len(targets)):
                target_rpc = fibers_config.fibersMap.get(targets[i])
                graph_capacity = capacitys[i]*CKB_UNIT
                if udt ==None:
                    graph_capacity = graph_capacity-62*100000000
                # print('current:',{'node_1': source_rpc.node_info()['node_id'], 'node_2': target_rpc.node_info()['node_id'], 'capacity': graph_capacity,'udt_type_script':udt})
                # print('ledger_channels:',ledger_channels)
                if {'node_1': source_rpc.node_info()['node_id'], 'node_2': target_rpc.node_info()['node_id'], 'capacity': graph_capacity,'udt_type_script':udt} in ledger_channels:
                    print("skip channel if cap in ledger_channels")
                    continue
                if {'node_1': target_rpc.node_info()['node_id'], 'node_2': source_rpc.node_info()['node_id'], 'capacity': graph_capacity,'udt_type_script':udt} in ledger_channels:
                    print("skip channel if cap in ledger_channels in reverse")
                    continue
                
                print(f"Channel from {source_node_id} to {targets[i]} capis not exist.")
                not_exist_channels.append({
                    'node_1': source_node_id,
                    'node_2': targets[i],
                    'capacity': capacitys[i],
                })
                

    print("--- Check Connect Phase Complete ---")
    print(f"current channels:{len(ledger_channels)} expect channels:{total_channels}")
    print("----not exist channels -----")
    for channel in not_exist_channels:
        print(channel)
    



