import os
from typing import Dict, List
from threading import Thread

import util


WG_CONFIG_PATH = "/etc/wireguard"


def read_wg_configs():
	files = set([f for f in os.listdir(WG_CONFIG_PATH) if os.path.isfile(os.path.join(WG_CONFIG_PATH, f))])
	subnet_target_dict: Dict[str, List[Dict[str, str]]] = {}

	for fn in files:
		with open(os.path.join(WG_CONFIG_PATH, fn)) as f:
			config = f.readlines()
			for line in config:
				if line.find("AllowedIPs") == 0:
					parts = line.split("=")
					if len(parts) < 2:
						continue

					subnet_str = parts[1].strip()
					subnets = [s.strip() for s in subnet_str.split(',')]
					# first subnet is the VPC subnet
					# second subnet is the peer IP/32
					if len(subnets) != 2:
						continue

					if subnets[0] not in subnet_target_dict:
						subnet_target_dict[subnets[0]] = []

					subnet_target_dict[subnets[0]].append({
						"ip": subnets[1].split("/")[0],
						"interface_name": fn.split(".conf")[0],
						"target_subnet": subnets[0]
					})

	return {
		"targets": subnet_target_dict,
		"interfaces": files,
	}


def read_active_map(config):
	routes = util.execute_shell_command("ip route")
	active_dict = {}
	for target in config["targets"]:
		for route in routes.split("\n"):
			if route.find(target) == -1:
				continue

			if route.find("wg") == -1:
				continue

			for interface in config["targets"][target]:
				if route.find(interface["interface_name"]) != -1:
					active_dict[interface["interface_name"]] = interface

	return active_dict


def health_check(interfaces):
	result = {}
	threads = []

	def ping_and_report(interface):
		alive = util.ping_retry(interface["ip"], 3)
		result[interface["interface_name"]] = alive

	for interface in interfaces:
		t = Thread(target=lambda: ping_and_report(interface))
		threads.append(t)

	for t in threads:
		t.start()

	for t in threads:
		t.join()

	return result


def switch_traffic(from_interface, to_interface, subnet):
	util.execute_shell_command(f"ip route del {from_interface} dev {subnet}")
	util.execute_shell_command(f"ip route add {to_interface} dev {subnet}")


if __name__ == "__main__":
	config = read_wg_configs()
	active_map = read_active_map(config)
	result = health_check(active_map.items())
	for interface_name, alive in result.items():
		if alive:
			continue

		subnet = active_map[interface_name]["target_subnet"]
		fail_overs = health_check(config[active_map[interface_name]["target_subnet"]])
		for new_interface_name, new_alive in fail_overs:
			if new_alive:
				switch_traffic(interface_name, new_interface_name, subnet)
