import random
import toml

def change_config(config):
    # 
    # [[connect_to]]
    # id = "relay_18"
    # type = "relay"
    # targets = [ "core_10", "core_4", "relay_28", "relay_25", "relay_14", "relay_31", "relay_38", "relay_2", "relay_1", "relay_37", "relay_3",]
    # capacitys = [ 90799, 28610, 99769, 3205, 291226, 931352, 852909, 190428, 826819, 211106, 308899,]
    # 修改relay 节点capacitys 为1w～2w 范围
    

    for j in range(len(config['connect_to'])):
        if config['connect_to'][j]['id'].startswith('relay'):
            for i in range(len(config['connect_to'][j]['capacitys'])):
                config['connect_to'][j]['capacitys'][i] = random.randint(10000, 20000)
        if config['connect_to'][j]['id'].startswith('edge'):
            for i in range(len(config['connect_to'][j]['capacitys'])):
                config['connect_to'][j]['capacitys'][i] = random.randint(10000, 20000)
    # save config.toml
    with open('config.new.toml', 'w') as f:
        toml.dump(config, f)