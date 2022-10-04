import os
from typing import Dict, List

from icmplib import ping

WG_CONFIG_PATH = "/home/gabriel/personal-projects/wireguard-cluster-setup/result/139.180.139.90/wireguard"


def read_wg_configs():
	files = [f for f in os.listdir(WG_CONFIG_PATH) if os.path.isfile(os.path.join(WG_CONFIG_PATH, f))]
	files = [os.path.join(WG_CONFIG_PATH, f) for f in files if f.find("wg") == 0]
	subnet_target_dict: Dict[str, List[str]] = {}

	for fn in files:
		with open(fn) as f:
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

					subnet_target_dict[subnets[0]].append(subnets[1])

	print(subnet_target_dict)


if __name__ == "__main__":
	read_wg_configs()
