#!/usr/bin/env python3

# Map this file to /tftpboot/ for vrnet vr-sros VMs to access via tftp
import sys
from pysros.management import connect
import pynetbox, requests

def connectNetbox(nbUrl = "http://172.20.20.1:8000"):

    ####
    # Set global HTTP retry strategy
    ####
    from requests.adapters import HTTPAdapter
    import urllib3
    from urllib3.util import Retry

    retry_strategy = Retry(
        total=3,backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        method_whitelist=["HEAD", "GET", "OPTIONS", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    http = requests.Session()
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    http.verify = False  # Disable SSL verify
    http.mount("https://", adapter)
    http.mount("http://", adapter)

    response = http.post(f'{nbUrl}/api/users/tokens/provision/',
                         json={ "username": "admin", "password": "admin" },
                         timeout=5 )
    response.raise_for_status() # Throw exception if error
    nbToken = response.json()['key']
    nb = pynetbox.api(nbUrl, token=nbToken)
    nb.http_session = http
    return nb

def createDeviceType(deviceTypeName, portCount, nb):
    nokia = nb.dcim.manufacturers.get(slug='nokia')
    if not nokia:
       nokia = nb.dcim.manufacturers.create({'name': "Nokia", 'slug': "nokia"})

    platform = nb.dcim.platforms.get(slug='sros')
    if not platform:
       # Uses SRLinux specific NAPALM driver: https://github.com/napalm-automation-community/napalm-srlinux
       platform = nb.dcim.platforms.create( { 'name': 'SROS', 'slug': 'sros',
                  'manufacturer': nokia.id,
                  'napalm_driver': 'sros', 'napalm_args': { 'insecure': True } } ) # skip_verify not used

    dev_type = nb.dcim.device_types.filter(name=deviceTypeName)
    if not dev_type:
        try:
            dev = {
             'name': deviceTypeName,
             'slug': deviceTypeName.lower(),
             'manufacturer': str(nokia.id),
            }
            dev_type = nb.dcim.device_types.create(dev)
            print(f'Device Type Created: {dt.manufacturer.name} - '
                  + f'{dt.model} - {dt.id}')
        except pynetbox.RequestError as e:
            print(e.error)
    else:
        dev_type = dev_type[0]

    createInterfaces(portCount, dev_type.id, nb)

def createInterfaces(portCount, deviceType, nb):
    all_interfaces = {str(item): item for item in nb.dcim.interface_templates.filter(devicetype_id=deviceType)}
    need_interfaces = []
    for i in range(1,portCount+1):
        portname = "1/1/c%d" % i
        try:
            ifGet = all_interfaces[portname]
            print(f'Interface Template Exists: {ifGet.name} - {ifGet.type}'
                  + f' - {ifGet.device_type.id} - {ifGet.id}')
        except KeyError:
            intf = {
              'name': portname,
              'type': '400gbase-x-qsfpdd',
              'device_type': deviceType,
            }
            need_interfaces.append(intf)

    if not need_interfaces:
        return

    try:
        ifSuccess = nb.dcim.interface_templates.create(need_interfaces)
        for intf in ifSuccess:
            print(f'Interface Template Created: {intf.name} - '
              + f'{intf.type} - {intf.device_type.id} - '
              + f'{intf.id}')
    except pynetbox.RequestError as e:
        print(e.error)

credentials = {
    "host": "clab-mpls-iot-lab-sros1.pop2",
    "username": "admin",
    "password": "admin",
    "port": 830,
    "hostkey_verify": False,
}

c = connect( **credentials )

#
# Uses Netconf to retrieve SROS YANG model config and/or system state
#
platform = c.running.get("/nokia-state:state/system/platform")
print( "/nokia-state:state/system/platform: %s" % platform )

# "configure": {
#             "nokia-conf:card": [
#               {
#                 "fp": [
#                   {
#                     "fp-number": 1
#                   },
#                   {
#                     "fp-number": 2
#                   }
#                 ],
#                 "mda": [
#                   {
#                     "mda-slot": 1,
#                     "mda-type": "s36-100gb-qsfp28"

# Read MDA type(s)
mda_type = c.running.get("/nokia-state:state/card[slot-number=1]/mda[mda-slot=1]/equipped-type")
print( "/nokia-state:state/card[slot-number=1]/mda[mda-slot=1]/equipped-type: %s" % mda_type )

cards = c.running.get("/nokia-state:state/card")
for cr in cards:
  print( "All cards? %s" % cards[cr] )
  print( cards[cr]['installed-mda-slots'] )
  print( cards[cr]['mda'] )
  print( cards[cr]['mda'][1]['equipped-ports'] )

#
# Create or update device in Netbox
#
nb = connectNetbox()
createDeviceType(platform,cards[1]['mda'][1]['equipped-ports'],nb)

# Be a good netizen
sys.exit( 0 )
