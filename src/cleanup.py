from concurrent.futures import ThreadPoolExecutor
import time
from src.config import FibersConfig

def shutdown_nodes(config):
    print("--- Running Cleanup Phase: Shutting Down Nodes ---")
    fibers_config = FibersConfig(config)
    for fiber_key in fibers_config.fibersMap.keys():
        fiber = fibers_config.fibersMap.get(fiber_key)
        default_script = fiber.node_info()['default_funding_lock_script']
        for channel in fiber.list_channels({})["channels"]:
            fiber.shutdown_channel({
                "channel_id": channel["channel_id"],
                "close_script": default_script,         
            })
        wait_channel_size_eq(fiber,0,120)
        print(f"{fiber_key} finished")


def wait_channel_size_eq(fiber,channels_size,timeout):
    
    for i in range(timeout):
        channels = fiber.list_channels({})["channels"]
        if len(channels) == channels_size:
            break
        time.sleep(1)
    if len(channels) != channels_size:
        raise TimeoutError(f"channel size not eq {channels_size} within timeout period.")