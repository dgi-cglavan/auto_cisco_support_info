"""Tools script that holds a variety of functions"""
import os
import requests
from genie.utils import Dq
from ratelimit import limits, RateLimitException, sleep_and_retry

"""Define API rate limits"""
call_int = 1
call_max = 5

def nornir_set_creds(norn, username=None, password=None):
    """
    Handler so credentials are not stored in cleartext.
    Thank you Kirk!
    """
    if not username:
        username = os.environ.get("NORNIR_USER")
    if not password:
        password = os.environ.get("NORNIR_PASS")

    for host_obj in norn.inventory.hosts.values():
        host_obj.username = username
        host_obj.password = password

    #for host in norn.inventory.hosts.keys():
    #    norn.inventory.hosts[host].connection_options['napalm'].extras['optional_args']['secret'] = os.environ.get("NORNIR_SECRET")


def manu_year_cisco(value: str):
    """Calculates manufacture date from Cisco SN"""
    date = int(value[3:5])
    return f"{date + 1996}"

@sleep_and_retry
@limits(calls=call_max, period=call_int)
def product_info(serial: str, token: str):
    """Return ths base part ID from a serial number"""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://api.cisco.com/product/v1/information/serial_numbers/{serial}"
    req = requests.request("GET", url, headers=headers)
    content = req.json()
    return Dq(content).contains("base_pid").get_values("base_pid", 0)

@sleep_and_retry
@limits(calls=call_max, period=call_int)
def eox(serial: str, token: str):
    """Returns all eox information and replacement option from serial number"""
    device = {}
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://api.cisco.com/supporttools/eox/rest/5/EOXBySerialNumber/1/{serial}"
    req = requests.request("GET", url, headers=headers)
    content = req.json()
    if content["EOXRecord"][0]["EOXExternalAnnouncementDate"]["value"] == "":
        device["eos"] = "N/A"
        device["eosm"] = "N/A"
        device["ldos"] = "N/A"
        device["eocr"] = "N/A"
        device["replacement"] = "N/A"
    else:
        device["eos"] = Dq(content).contains("EndOfSaleDate").get_values("value", 0)
        device["eosm"] = (
            Dq(content).contains("EndOfSWMaintenanceReleases").get_values("value", 0)
        )
        device["ldos"] = (
            Dq(content).contains("LastDateOfSupport").get_values("value", 0)
        )
        device["eocr"] = (
            Dq(content).contains("EndOfServiceContractRenewal").get_values("value", 0)
        )
        device["replacement"] = (
            Dq(content)
            .contains("MigrationProductId")
            .get_values("MigrationProductId", 0)
        )
    return device

@sleep_and_retry
@limits(calls=call_max, period=call_int)
def software_release(productid: str, token: str):
    """Returns a list of reccomended software from product ID"""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://api.cisco.com/software/suggestion/v2/suggestions/software/productIds/{productid}"
    req = requests.request("GET", url, headers=headers)
    content = req.json()
    upgrade = (
        Dq(content)
        .contains_key_value("imageName", ".*universal.*", value_regex=True)
        .get_values("imageName")
    )
    if upgrade == []:
        upgrade = "Image Not Found"
    return upgrade

@sleep_and_retry
@limits(calls=call_max, period=call_int)
def sn2info(serial: str, token: str):
    """Returns coverage information from serial number"""
    coverage = {}
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://api.cisco.com/sn2info/v2/coverage/status/serial_numbers/{serial}"
    req = requests.request("GET", url, headers=headers)
    content = req.json()
    coverage["covered"] = (
            Dq(content).contains("is_covered").get_values("is_covered", 0)
    )
    #coverage["end_date"] = (
    #        Dq(content).contains("coverage_end_date").get_values("coverage_end_date", 0)
    #)
    if coverage["covered"] == "NO":
    #if content["serial_numbers"][0]["is_covered"] == "NO":
        coverage["end_date"] = "N/A"
    else:
        coverage["end_date"] = (
            Dq(content).contains("coverage_end_date").get_values("coverage_end_date", 0)
        )
    if coverage["covered"] == []:
        coverage["covered"] = "Unknown"
        coverage["end_date"] = "Unknown"
    return coverage
