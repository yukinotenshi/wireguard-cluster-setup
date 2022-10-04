from typing import TypedDict, Dict, List


class RouterType(TypedDict):
	id: int
	site_id: int
	wan_ip: str
	pvc_ip: str


class SiteType(TypedDict):
	id: int
	name: str
	subnet: str


class ConfigType(TypedDict):
	wg_subnet_prefix: int
	sites: List[SiteType]
	routers: List[RouterType]

