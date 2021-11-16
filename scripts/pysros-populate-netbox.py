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

def slugFormat(name):
    return name.lower().replace(' ', '_')

def createDeviceType(deviceTypeName, cards, nb):
    nokia = nb.dcim.manufacturers.get(slug='nokia')
    if not nokia:
       nokia = nb.dcim.manufacturers.create({'name': "Nokia", 'slug': "nokia"})

    platform = nb.dcim.platforms.get(slug='sros')
    if not platform:
       # Uses SRLinux specific NAPALM driver: https://github.com/napalm-automation-community/napalm-srlinux
       platform = nb.dcim.platforms.create( { 'name': 'SROS', 'slug': 'sros',
                  'manufacturer': nokia.id,
                  'napalm_driver': 'sros', 'napalm_args': { 'insecure': True } } ) # skip_verify not used

    dev_type = nb.dcim.device_types.get(name=deviceTypeName)
    if not dev_type:
        try:
            dev = {
             'model': deviceTypeName,
             'slug': slugFormat(deviceTypeName),
             'manufacturer': nokia.id,
            }
            dev_type = nb.dcim.device_types.create(dev)
            print(f'Device Type Created: {dev_type.manufacturer.name} - '
                  + f'{dev_type.model} - {dev_type.id}')
        except pynetbox.RequestError as e:
            print(e.error)

    createInterfaces(1,None,1,'100base-tx',dev_type.id, nb)
    for c in cards:
       for m in cards[c]['mda']:
          portCount = int( str( cards[c]['mda'][m]['equipped-ports']) )
          mdaType = str( cards[c]['mda'][m]['equipped-type'] )
          portType = '100gbase-x-qsfp28' if 'qsfp' in mdaType else '400gbase-x-qsfpdd'
          print( "Card %d MDA %d: ports %d type=%s => %s" % (c,m,portCount,mdaType,portType) )
          createInterfaces(c, m, portCount, portType, dev_type.id, nb)

def createInterfaces(card, mda, portCount, portType, deviceType, nb):
    all_interfaces = {str(item): item for item in nb.dcim.interface_templates.filter(devicetype_id=deviceType)}
    need_interfaces = []
    for i in range(1,portCount+1):
        portname = "%d/%d/c%d" % (card,mda,i) if mda else "A/1"
        try:
            ifGet = all_interfaces[portname]
            print(f'Interface Template Exists: {ifGet.name} - {ifGet.type}'
                  + f' - {ifGet.device_type.id} - {ifGet.id}')
        except KeyError:
            intf = {
              'name': portname,
              'type': portType,
              'device_type': deviceType,
              'mgmt_only': not mda
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

def createDeviceInstance(device_name,mgmt_ipv4,nb):
    new_chassis = nb.dcim.devices.get(name=device_name)
    if not new_chassis:
       new_chassis = nb.dcim.devices.create(
         name=device_name,
         # See https://github.com/netbox-community/devicetype-library/blob/master/device-types/Nokia/7210-SAS-Sx.yaml
         device_type=dev_type.id,
         serial=mac,
         device_role=role.id,
         site=site.id, # Cannot be None
         platform=platform.id, # Optional, used for NAPALM driver too
         tenant=None,
         rack=None,
         tags=[],
       )

    # Now assign the IP to the mgmt interface
    mgmt = nb.dcim.interfaces.get(name='A/1', device=device_name)
    logging.info( f"mgmt interface: {mgmt}")
    # ip.assigned_object_id = mgmt.id
    # ip.assigned_object_type = mgmt.type
    ip = nb.ipam.ip_addresses.get(address=mgmt_ipv4)
    if not ip:
       ip = nb.ipam.ip_addresses.create(address=mgmt_ipv4,dns_name=device_name)
    ip.device = new_chassis.id
    ip.interface = mgmt.id
    ip.primary_for_parent = True
    ip.dns_name = device_name
    ip.save()

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
  print( cards[cr]['installed-mda-slots'] )
  for m in cards[cr]['mda']:
     print( cards[cr]['mda'][m]['equipped-ports'] )

#
# Create or update device in Netbox
#
nb = connectNetbox()
createDeviceType( str(platform), cards, nb)

hostname = c.running.get("/nokia-conf:configure/system/hostname")
print( hostname )

mgmt_ip = c.running.get("/nokia-conf:configure/port[name=A/1]")
print( mgmt_ip )

# Be a good netizen
sys.exit( 0 )
