import time
import logging
from src.config import FibersConfig

LOGGER = logging.getLogger(__name__)


def reconnect(config):
    """Repeatedly disconnect and reconnect peers for a given duration.

    Config example::

        [[reconnect]]
        ids = ["TestNet_0"]
        target = ["TestNet_1"]
        interval = 0.1
        duration = 604800
    """
    fibers_config = FibersConfig(config)

    if 'reconnect' not in config:
        print("No reconnect config found")
        return

    for reconnect_config in config['reconnect']:
        ids = reconnect_config.get('ids', [])
        targets = reconnect_config.get('target', [])
        interval = reconnect_config.get('interval', 1)
        duration = reconnect_config.get('duration', 60)

        if len(ids) != len(targets):
            raise Exception(f"ids len:{len(ids)} != target len:{len(targets)}")

        # Resolve RPC clients and target pubkeys
        pairs = []
        for i in range(len(ids)):
            source_id = ids[i]
            target_id = targets[i]
            source_rpc = fibers_config.fibersMap.get(source_id)
            target_rpc = fibers_config.fibersMap.get(target_id)
            if source_rpc is None:
                raise Exception(f"source id:{source_id} not found in fibers config")
            if target_rpc is None:
                raise Exception(f"target id:{target_id} not found in fibers config")
            target_pubkey = target_rpc.node_info()["pubkey"]
            target_address = target_rpc.node_info()["addresses"][0]
            pairs.append({
                "source_id": source_id,
                "target_id": target_id,
                "source_rpc": source_rpc,
                "target_pubkey": target_pubkey,
                "target_address": target_address,
            })

        print(f"--- Running Reconnect: ids={ids} targets={targets} interval={interval} duration={duration} ---")
        start_time = time.time()
        cycle = 0
        while time.time() - start_time < duration:
            cycle += 1
            for pair in pairs:
                try:
                    pair["source_rpc"].disconnect_peer({"pubkey": pair["target_pubkey"]})
                    pair["source_rpc"].connect_peer({"address": pair["target_address"]})
                    LOGGER.info(f"cycle:{cycle} reconnect {pair['source_id']} -> {pair['target_id']} success")
                except Exception as e:
                    LOGGER.debug(f"cycle:{cycle} reconnect {pair['source_id']} -> {pair['target_id']} error: {e}")
            time.sleep(interval)

        elapsed = time.time() - start_time
        print(f"--- Reconnect Complete: {cycle} cycles in {elapsed:.2f}s ---")
