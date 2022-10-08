import subprocess

from icmplib import ping



def generate_wg_keypair() -> (str, str):
	p = subprocess.Popen("wg genkey", stdout=subprocess.PIPE, shell=True)
	private_key = p.stdout.read().decode("utf-8")
	p = subprocess.Popen(
		"echo '{}' | wg pubkey".format(private_key),
		stdout=subprocess.PIPE,
		shell=True
	)
	public_key = p.stdout.read().decode("utf-8")

	return private_key.strip(), public_key.strip()


def execute_shell_command(command: str) -> str:
	p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
	return p.stdout.read().decode("utf-8")


def ping_retry(address, retry=0):
	host = None
	while retry >= 0:
		try:
			host = ping(address, count=1, interval=1, timeout=0.5, privileged=False)
		except:
			retry -= 1
			continue

		if not host.is_alive:
			retry -= 1
		else:
			retry = -1

	return host or host.is_alive
