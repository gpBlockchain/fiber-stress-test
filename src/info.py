
from src.config import FibersConfig

def info(config):
    fibers_config = FibersConfig(config)
    for key in fibers_config.fibersMap.keys():
        try:
            channel =  fibers_config.fibersMap[key].list_channels({})
            peers_info = fibers_config.fibersMap[key].list_peers()
            print(f"cur id:{key} channel size:{len(channel['channels'])} peer size:{len(peers_info['peers'])}")
        except Exception as e:
            print(f"cur id:{key} failed:",e)