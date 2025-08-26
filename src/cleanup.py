import time
from tkinter import E
from src.config import FibersConfig
from src.fiber_rpc import CKB_UNIT

def shutdown_nodes(config):
    print("--- Running Cleanup Phase: Shutting Down Nodes ---")
    fibers_config = FibersConfig(config)
    # 获取connnect_to
    # target id 获取和当前node的channel id
    # target 关闭channel ，将close_script填id
    for connection in config['connect_to']:
        from_id = connection.get('id')
        print(f"from_id {from_id}")

        from_fiber = fibers_config.fibersMap.get(from_id)
        try:
            channels = from_fiber.list_channels({})
        except Exception as e:
            print(f"from_id {from_id}: {e}")
            continue
        print(f"from_id {from_id} channels len: {len(channels['channels'])}")
        if len(channels['channels']) == 0:
            continue
        try:
            from_fiber_peer_id = from_fiber.node_info()["addresses"][0].split("/")[-1]
        except Exception as e:
            print(f"from_id {from_id} error {e}")
            continue
        for i in range(len(connection.get('targets'))):
            target_id = connection.get('targets')[i]
            target_fiber = fibers_config.fibersMap.get(target_id)
            try:
                channels = target_fiber.list_channels({
                    "peer_id": from_fiber_peer_id,
                })["channels"]
            except Exception as e:
                print(f"target_id {target_id} error {e}")
                continue
            print(f"target_id {target_id} channels len: {len(channels)}")
            udt = connection.get('udt',None)
            for channel in channels:
                channel_balance = int(channel["local_balance"],16)+ int(channel["remote_balance"],16)
                if udt is None:
                    ckb_deposit = -62*CKB_UNIT
                    channel_balance -= ckb_deposit
                if (channel_balance == connection.get("capacitys")[i]*CKB_UNIT ):
                    if channel['state']['state_name'] == 'CHANNEL_READY':
                        try:
                            target_fiber.shutdown_channel({
                                "channel_id": channel["channel_id"],
                                "close_script": from_fiber.node_info()['default_funding_lock_script'],
                                "fee_rate":"0x3FC"
                            })
                        except:
                            pass
                        print(f"channel {channel['channel_id']} shutdown success")
                        time.sleep(0.1)
                        continue
                    else:
                        print(f"channel {channel['channel_id']} status is {channel['state']}")
                else:
                    print(f"channel {channel['channel_id']} balance is not equal,local_balance: {int(channel['local_balance'],16)} remote_balance: {int(channel['remote_balance'],16)} current balance: {channel_balance} not eq: {connection.get('capacitys')[i]*CKB_UNIT}")


def force_shutdown(config):
    print("--- Running Cleanup Phase: Shutting Down Nodes ---")
    fibers_config = FibersConfig(config)
    # 获取connnect_to
    # target id 获取和当前node的channel id
    # target 关闭channel ，将close_script填id
    for connection in config['connect_to'][12+39+37:]:
        from_id = connection.get('id')
        print(f"from_id {from_id}")

        from_fiber = fibers_config.fibersMap.get(from_id)
        channels = from_fiber.list_channels({})
        print(f"from_id {from_id} channels len: {len(channels['channels'])}")
        for channel in channels['channels']: 
            if channel['state']['state_name'] == 'CHANNEL_READY':
                try:
                    from_fiber.shutdown_channel({
                        "channel_id": channel["channel_id"],
                        # "close_script": from_fiber.node_info()['default_funding_lock_script'],
                        # "fee_rate":"0x3FC",
                        "force": True
                    })
                except Exception as e:
                    print(f"channel {channel['channel_id']} ,channel msg:{channel} shutdown failed, error: {e}")
                    pass
                print(f"channel {channel['channel_id']} shutdown success")
                time.sleep(0.1)
                continue
            

def wait_channel_size_eq(fiber,channels_size,timeout):
    
    for i in range(timeout):
        channels = fiber.list_channels({})["channels"]
        if len(channels) == channels_size:
            break
        time.sleep(1)
    if len(channels) != channels_size:
        raise TimeoutError(f"channel size not eq {channels_size} within timeout period.")