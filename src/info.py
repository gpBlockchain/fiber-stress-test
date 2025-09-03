
from src.config import FibersConfig

def info(config):
    fibers_config = FibersConfig(config)
    for key in fibers_config.fibersMap.keys():
        print(f"key:{key},url:{fibers_config.fibersMap[key].url}")
        try:
            channel =  fibers_config.fibersMap[key].list_channels({"include_closed":True})
            udt_channels_size = 0
            ckb_channels_size = 0
            shutdown_channels_size = 0
            closed_channels_size = 0
            for item in channel['channels']:
                if item['state']['state_name'] == 'SHUTTING_DOWN':
                    shutdown_channels_size += 1
                if item['state']['state_name'] == 'CLOSED':
                    closed_channels_size += 1
                if item['state']['state_name'] == 'CHANNEL_READY':
                    if item['funding_udt_type_script'] is not None:
                        udt_channels_size += 1
                    else:
                        ckb_channels_size += 1
                else:
                    print(item['state']['state_name'])
            peers_info = fibers_config.fibersMap[key].list_peers()
            print(f"cur id:{key} url:{fibers_config.fibersMap[key].url} udt channel size:{udt_channels_size} ckb channel size:{ckb_channels_size} peer size:{len(peers_info['peers'])},shutdown_channels_size:{shutdown_channels_size},close_channels_size:{closed_channels_size}")
        except Exception as e:
            print(f"cur id:{key} url:{fibers_config.fibersMap[key].url} failed:",e)
