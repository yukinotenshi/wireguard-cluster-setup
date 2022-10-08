import os
import json
from random import randint
from typing import List, Dict

import yaml

import util
from model import RouterType, SiteType, ConfigType


def load_config() -> ConfigType:
    with open("config.json") as f:
        data = f.read()
        conf = json.loads(data)

    return conf


def load_wg_template() -> str:
    with open("templates/wireguard_config.template") as f:
        return f.read()


class WireGuardConfigGenerator:
    def __init__(self):
        self.config = load_config()
        self.template = load_wg_template()
        self.wg_configs: Dict[str, Dict[str, str]] = {}

    def generate_all(self):
        router_dict: Dict[int, RouterType] = {}
        site_dict: Dict[int, SiteType] = {}
        for site in self.config['sites']:
            site_dict[site['id']] = site
        for router in self.config['routers']:
            router_dict[router['id']] = router

        start_port = randint(12000, 30000)
        c = 1
        for i in range(len(self.config['routers'])):
            from_router: RouterType = self.config['routers'][i]
            for j in range(i+1, len(self.config['routers'])):
                to_router: RouterType = self.config['routers'][j]
                if to_router['site_id'] == from_router['site_id']:
                    continue

                from_router_keys = util.generate_wg_keypair()
                to_router_keys = util.generate_wg_keypair()
                from_wg_config_vars = {
                    "from_server_wg_ip": f"{self.config['wg_subnet_prefix']}.{from_router['site_id']}.{from_router['id']}.{c}",
                    "to_server_wg_ip": f"{self.config['wg_subnet_prefix']}.{to_router['site_id']}.{to_router['id']}.{c}",
                    "from_server_private_key": from_router_keys[0],
                    "from_server_listen_port": start_port+c,
                    "to_server_public_key": to_router_keys[1],
                    "to_server_wan_ip": to_router['wan_ip'],
                    "to_server_listen_port": start_port+c,
                    "to_server_subnet": site_dict[to_router['site_id']]['subnet'],
                }
                to_wg_config_vars = {
                    "from_server_wg_ip": from_wg_config_vars["to_server_wg_ip"],
                    "to_server_wg_ip": from_wg_config_vars["from_server_wg_ip"],
                    "from_server_private_key": to_router_keys[0],
                    "from_server_listen_port": start_port + c,
                    "to_server_public_key": from_router_keys[1],
                    "to_server_wan_ip": from_router['wan_ip'],
                    "to_server_listen_port": start_port + c,
                    "to_server_subnet": site_dict[from_router['site_id']]['subnet'],
                }
                from_wg_config = self.template.format(**from_wg_config_vars)
                to_wg_config = self.template.format(**to_wg_config_vars)

                if from_router['wan_ip'] not in self.wg_configs:
                    self.wg_configs[from_router['wan_ip']] = {}

                if to_router['wan_ip'] not in self.wg_configs:
                    self.wg_configs[to_router['wan_ip']] = {}

                self.wg_configs[from_router['wan_ip']][f"wg{site_dict[to_router['site_id']]['name']}{c}"] = from_wg_config
                self.wg_configs[to_router['wan_ip']][f"wg{site_dict[from_router['site_id']]['name']}{c}"] = to_wg_config
                c += 1

    def dump_to_folder(self, folder_name: str):
        if not os.path.exists(folder_name):
            os.mkdir(folder_name)

        for ip, configs in self.wg_configs.items():
            cur_path = os.path.join(folder_name, ip)
            if not os.path.exists(cur_path):
                os.mkdir(cur_path)

            cur_path = os.path.join(cur_path, "wireguard")
            if not os.path.exists(cur_path):
                os.mkdir(cur_path)

            for name, c in configs.items():
                with open(os.path.join(cur_path, f"{name}.conf"), 'w') as f:
                    f.write(c)

    def dump_inventory(self, folder_name: str):
        inventory: Dict = {
            "routers": {
                "hosts": {

                },
                "vars": {
                    "peers": [

                    ]
                }
            }
        }
        for ip, configs in self.wg_configs.items():
            inventory["routers"]["vars"]["peers"].append(ip)
            inventory["routers"]["hosts"][ip] = {
                "wg_configs": [],
            }
            for name in configs.keys():
                inventory["routers"]["hosts"][ip]["wg_configs"].append(name)

        with open(os.path.join(folder_name, "inventory"), "w") as f:
            yaml.dump(inventory, f)


if __name__ == "__main__":
    generator = WireGuardConfigGenerator()
    generator.generate_all()
    generator.dump_to_folder("playbook/files/per_host")
    generator.dump_inventory("playbook")
