#!/usr/bin/env python3

# Map this file to /tftpboot/ for vrnet vr-sros VMs to access via tftp:
# pyexec tftp://172.31.255.29/pysros-demo.py
import sys
# import os  # does not work - "no module named 'os'"
from pysros.management import connect


c = connect()

#
# Uses Netconf to retrieve SROS YANG model config and/or system state
#
pysros_ds = c.running.get("/nokia-conf:configure/system/name")
print( "/nokia-conf:configure/system/name: %s" % pysros_ds )

print( "sys.version: %s" % sys.version ) # 3.4.0 on SROS 21.7R3
print( "sys.path: %s" % sys.path ) # [] on SROS 21.7R3

# Import local packages
sys.path.append( "cf3:/" )
import pynetbox
print( "PyNetbox imported ok" )

# Be a good netizen
sys.exit( 0 )
