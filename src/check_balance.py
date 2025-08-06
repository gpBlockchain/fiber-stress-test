from src.config import FibersConfig
import logging

LOGGER = logging.getLogger(__name__)


def check_balance(config):
    print("--- Running Preparation Phase: Connecting Nodes ---")
    fibers_config = FibersConfig(config)
    total_capacity = 0    
    if 'connect_to' in config:
        for connection in config['connect_to']:
            targets = connection.get('targets', [])
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
            total_capacity += capacitys_sum
            print(f"fiber id:{connection.get('id')} need capacity:{capacitys_sum}")
                # todo check capacity enough
                # skip channel if cap in ledger_channels
    print(f"total capacity:{total_capacity}")
    print("--- Preparation Phase Complete ---")

