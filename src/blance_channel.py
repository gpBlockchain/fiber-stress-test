from src.config import FibersConfig
from src.fiber_rpc import wait_payment_state

def balance_channels(config):
    # 查询channels 
    fibers_config = FibersConfig(config)
    for key in fibers_config.fibersMap.keys():
        print(f"current key:{key}")
        fiber = fibers_config.fibersMap[key]
        try:
            list_peers = fiber.list_peers()
            chanels = fiber.list_channels({})
        except Exception as e:
            print(f"key:{key} list channels failed: {e}")
            continue
        for channel in chanels['channels']:
            if channel['remote_balance'] == "0x0":
                print(f"key:{key} channel id:{channel['channel_id']}")
                peer_id = channel['peer_id']
                pubkey = None
                for peer in list_peers['peers']:
                    if peer['peer_id'] == peer_id:
                        pubkey = peer['pubkey']
                        break
                
                if pubkey is None:
                    print(f"Error: key:{key} channel id:{channel['channel_id']} - peer_id {peer_id} not found in peers list")
                    continue
                try:
                    payment = fiber.send_payment({
                        "target_pubkey": pubkey,
                        "amount": hex(int(int(channel['local_balance'],16)/2)) ,
                        "keysend":True,
                        "udt_type_script": channel['funding_udt_type_script'],
                    })
                    wait_payment_state(fiber, payment["payment_hash"], "Success",timeout=150, interval=0.1)
                    print(f"key:{key} channel id:{channel['channel_id']} payment success")
                except Exception as e:
                    print(f"key:{key} channel id:{channel['channel_id']} payment failed: {e}")
                        
                

                    
                