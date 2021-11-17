#!/usr/bin/env python3

# Map this file to /tftpboot/ for vrnet vr-sros VMs to access via tftp
import sys, ipaddress, re
from pysros.management import connect
import pynetbox, requests

# Helper method
def get_ips_by_dns_lookup(target, port=22):
    '''
        this function takes the passed target and optional port and does a dns
        lookup. it returns the ips that it finds to the caller.

        :param target:  the URI that you'd like to get the ip address(es) for
        :type target:   string
        :param port:    which port do you want to do the lookup against?
        :type port:     integer
        :returns ips:   all of the discovered ips for the target
        :rtype ips:     list of strings

    '''
    import socket
    return list(map(lambda x: x[4][0], socket.getaddrinfo(target,port,type=socket.SOCK_STREAM)))

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

    return dev_type.id, platform.id

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

def createDeviceInstance(device_name,mgmt_ipv4,dev_type_id,platform_id,nb):
       role_site = re.match( "^(\S+)\d+[.](.*)$", device_name )
       if role_site:
          role_str = "edge-router" # role_site.groups()[0]
          role = nb.dcim.device_roles.get(slug=slugFormat(role_str))
          if not role:
             role = nb.dcim.device_roles.create({ 'name': role_str, 'slug': slugFormat(role_str) })

          site_str = role_site.groups()[1]
          site = nb.dcim.sites.get(slug=slugFormat(site_str))
          if not site:
             site = nb.dcim.sites.create({ 'name': site_str, 'slug': slugFormat(site_str) })

          new_chassis = nb.dcim.devices.get(name=device_name)
          if not new_chassis:
             new_chassis = nb.dcim.devices.create(
              name=device_name,
              # See https://github.com/netbox-community/devicetype-library/blob/master/device-types/Nokia/7210-SAS-Sx.yaml
              device_type=dev_type_id,
              serial=1234, # TODO system MAC
              device_role=role.id,
              site=site.id, # Cannot be None
              platform=platform_id, # Optional, used for NAPALM driver too
              tenant=None,
              rack=None,
              tags=[],
             )
          print( dict(new_chassis) )

          # Now assign the IP to the mgmt interface
          mgmt = nb.dcim.interfaces.get(name='A/1', device=device_name)
          print( f"mgmt interface: {dict(mgmt)}")
          # ip.assigned_object_id = mgmt.id
          # ip.assigned_object_type = mgmt.type
          if mgmt:
             ip = nb.ipam.ip_addresses.get(address=mgmt_ipv4)
             if not ip:
                ip = nb.ipam.ip_addresses.create(address=mgmt_ipv4,dns_name=device_name)
             print( f"IP:{dict(ip)}" )

             # new_chassis.primary_ip = ip.id
             # new_chassis.save()

             # ip.device = new_chassis.id
             # # ip.status = "active"
             # ip.interface = mgmt.id
             # ip.assigned_object = mgmt.id
             ip.assigned_object_id = mgmt.id
             ip.assigned_object_type = "dcim.interface"
             ip.primary_for_parent = True # "on"
             ip.dns_name = device_name
             ip.save() # Note: make sure to run latest pynetbox release
          else:
             print( "Unable to find A/1 mgmt interface" )

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
dev_type_id, platform_id = createDeviceType( str(platform), cards, nb)

hostname = str( c.running.get("/nokia-conf:configure/system/name") )
print( hostname )

# Due to the way containerlab works, lookup IP using DNS
mgmt_ips = get_ips_by_dns_lookup( credentials['host'] )
print( mgmt_ips )
ipv4s = [ ip for ip in mgmt_ips if ipaddress.ip_address(ip).version == 4 ]

if ipv4s:
   try:
     createDeviceInstance( hostname, ipv4s[0], dev_type_id, platform_id, nb )
   except Exception as ex:
     print( ex )

# Be a good netizen
sys.exit( 0 )
