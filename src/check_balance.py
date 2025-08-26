from src.config import FibersConfig
from src.fiber_rpc import CKB_UNIT
from src.rpc import get_ckb_balance, get_udt_balance,RPCClient
import logging

LOGGER = logging.getLogger(__name__)
 

def check_balance(config):
    print("--- Running Preparation Phase: Connecting Nodes ---")
    fibers_config = FibersConfig(config)
    ckbClient = RPCClient(config.get("ckb").get("url"))
    total_capacity = {'ckb':0}
    fiber_capacity_map = {}
    for key in fibers_config.fibersMap.keys():
        fiber_capacity_map[key] = {}
        fiber_capacity_map[key]['deposit_ckb'] = 0
        fiber_capacity_map[key]['udt'] = {}
        fiber_capacity_map[key]['ckb'] =  {'balance': 0, 'need': 0}
    if 'connect_to' in config:
        for connection in config['connect_to']:
            print("current id:",connection.get('id'))
            targets = connection.get('targets', [])
            capacitys = connection.get('capacitys', [])
            capacitys_sum = {'ckb':0,'udt':0}
            #  check capcitys len == targets len
            if len(capacitys) != len(targets):
                raise Exception(f"capacitys len:{len(capacitys)} != targets len:{len(targets)}")
            #  check target id exist
            for target in targets:
                if target not in fibers_config.fibersMap:
                    raise Exception(f"target id:{target} not exist")
            udt = connection.get('udt',None)
            key = udt != None and udt['args'] or 'ckb'
            capacitys_sum[key] = 0
            if key not in total_capacity.keys():
                total_capacity[key] = capacitys_sum[key]
            for i in range(len(capacitys)):
                capacitys_sum[key] += capacitys[i]
            total_capacity[key] += capacitys_sum[key]
            try:
                account_lock = fibers_config.fibersMap[connection.get('id')].node_info()['default_funding_lock_script']
            except Exception as e:
                print(f"id {connection.get('id')} error {e}")
                continue
            if key == 'ckb':
                ckb_balance = get_ckb_balance(ckbClient, account_lock)
                fiber_capacity_map[connection.get('id')]['ckb'] = {'balance':ckb_balance,'need':capacitys_sum[key]*CKB_UNIT}
            else:
                udt_balance = get_udt_balance(ckbClient, account_lock, udt)
                fiber_capacity_map[connection.get('id')]['udt'][key] = {'balance':udt_balance,'need':capacitys_sum[key]*CKB_UNIT}
            
            # get deposit balance
            # if udt，id deposit balance = 142*ckb * target length  
            if key == 'ckb':
                fiber_capacity_map[connection.get('id')]['deposit_ckb'] += 62*len(targets) * CKB_UNIT
                for target in targets:
                    fiber_capacity_map[target]['deposit_ckb'] += 62 * CKB_UNIT
            else:
                fiber_capacity_map[connection.get('id')]['deposit_ckb'] += 142*len(targets) * CKB_UNIT
                for target in targets:
                    fiber_capacity_map[target]['deposit_ckb'] += 142 * CKB_UNIT

    
    for key in fiber_capacity_map.keys():
        print(f"fiber id:{key}  data:{fiber_capacity_map[key]}")  
        # todo 打印余额不足的用户          
        if fiber_capacity_map[key]['ckb']['balance'] < fiber_capacity_map[key]['ckb']['need']+ fiber_capacity_map[key]['deposit_ckb']:
            print(f"fiber id:{key} ckb balance not enough, need:{fiber_capacity_map[key]['ckb']['need']+ fiber_capacity_map[key]['deposit_ckb']}, balance:{fiber_capacity_map[key]['ckb']['balance']}")
        for udt_key in fiber_capacity_map[key]['udt'].keys():
            if fiber_capacity_map[key]['udt'][udt_key]['balance'] < fiber_capacity_map[key]['udt'][udt_key]['need']:
                print(f"fiber id:{key} {udt_key} balance not enough, need:{fiber_capacity_map[key]['udt'][udt_key]['need']}, balance:{fiber_capacity_map[key]['udt'][udt_key]['balance']}")

            
    print(f"total capacity:{total_capacity}")
    print("--- Check Phase Complete ---")

