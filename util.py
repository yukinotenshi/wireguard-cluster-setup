import subprocess


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
