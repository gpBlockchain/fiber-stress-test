from src.config import FibersConfig



def graph_channels_info(config):
    fibers_config = FibersConfig(config)
    for key in fibers_config.fibersMap:
        fiber = fibers_config.fibersMap[key]
        try:
            channels = fiber.graph_channels({"limit": "0xffff"})
            print(f"fiber {key} channels len: {len(channels['channels'])}")
        except Exception as e:
            print(f"fiber {key} graph_channels error: {e}")
