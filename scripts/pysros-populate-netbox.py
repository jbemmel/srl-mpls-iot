#!/usr/bin/env python3

# Map this file to /tftpboot/ for vrnet vr-sros VMs to access via tftp
import sys
# import os  # does not work - "no module named 'os'"
from pysros.management import connect

# TODO import pynetbox

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
mda_type = c.running.get("/nokia-state:state/card[slot-number=1]/mda/equipped-type")
print( "/nokia-state:state/card[slot-number=1]/mda/equipped-type: %s" % mda_type )

#
# Create or update device in Netbox
#

# Be a good netizen
sys.exit( 0 )
