import os
import subprocess
from typing import Dict, List
from threading import Thread

from icmplib import ping

WG_CONFIG_PATH = "/etc/wireguard"


def ping_retry(address, retry=0):
	host = None
	ping(address, retry)
	while retry >= 0:
		try:
			host = ping(address, count=1, interval=1, timeout=0.5, privileged=False)
		except Exception as e:
			print(e)
			retry -= 1
			continue

		if not host.is_alive:
			retry -= 1
		else:
			retry = -1

	if not host:
		return False

	return host.is_alive


def execute_shell_command(command: str) -> str:
	p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
	return p.stdout.read().decode("utf-8")


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
	routes = execute_shell_command("ip route")
	active_dict = {}
	for target in config["targets"]:
		has_active_route = False
		for route in routes.split("\n"):
			if route.find(target) == -1:
				continue

			if route.find("wg") == -1:
				continue

			for interface in config["targets"][target]:
				if route.find(interface["interface_name"]) != -1:
					active_dict[interface["interface_name"]] = {
						**interface,
						"alive": True
					}
					has_active_route = True

		if not has_active_route:
			interface = config["targets"][target][0]
			active_dict[interface["interface_name"]] = {
				**interface,
				"alive": False
			}

	return active_dict


def health_check(interfaces):
	result = {}
	threads = []

	def ping_and_report(interface):
		nonlocal result
		if not interface.get("alive", True):
			result[interface["interface_name"]] = False
			return

		alive = ping_retry(interface["ip"], 3)
		result[interface["interface_name"]] = alive

	for interface in interfaces:
		t = Thread(target=ping_and_report, args=[interface])
		threads.append(t)

	for t in threads:
		t.start()

	for t in threads:
		t.join()

	return result


def switch_traffic(from_interface_name, to_interface_name, subnet):
	execute_shell_command(f"ip route del {subnet} dev {from_interface_name}")
	execute_shell_command(f"ip route add {subnet} dev {to_interface_name}")


def add_peer_route(interface):
	execute_shell_command(f"ip route add {interface['ip']} dev {interface['interface_name']}")


if __name__ == "__main__":
	config = read_wg_configs()
	for interfaces in config['targets'].values():
		for interface in interfaces:
			add_peer_route(interface)
	active_map = read_active_map(config)
	result = health_check(active_map.values())
	for interface_name, alive in result.items():
		if alive:
			continue

		print(f"{interface_name} is down")
		subnet = active_map[interface_name]["target_subnet"]
		fail_overs = health_check(config["targets"][subnet])
		for new_interface_name, new_alive in fail_overs.items():
			if new_alive:
				print(f"switching {interface_name} to {new_interface_name}")
				switch_traffic(interface_name, new_interface_name, subnet)
