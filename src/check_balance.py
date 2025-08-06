from src.config import CKB_UNIT, FibersConfig
from src.rpc import get_ckb_balance, RPCClient
import logging

LOGGER = logging.getLogger(__name__)


def check_balance(config):
    print("--- Running Preparation Phase: Connecting Nodes ---")
    fibers_config = FibersConfig(config)
    ckbClient = RPCClient(config.get("ckb").get("url"))
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
            account_lock = fibers_config.fibersMap[connection.get('id')].node_info()['default_funding_lock_script']
            ckb_balance = get_ckb_balance(ckbClient, account_lock)
            print(f"fiber id:{connection.get('id')} need capacity:{ckb_balance}/{capacitys_sum*CKB_UNIT} ok:{ckb_balance >= capacitys_sum*CKB_UNIT}, ckb_balance:{ckb_balance}")
            if ckb_balance < capacitys_sum*CKB_UNIT:
                print(f"fiber id:{connection.get('id')} script:{account_lock} ckb_balance:{ckb_balance} < capacitys_sum*CKB_UNIT:{capacitys_sum*CKB_UNIT}")

    print(f"total capacity:{total_capacity}")
    print("--- Preparation Phase Complete ---")

