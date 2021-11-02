# Map this file to /tftpboot/ for vrnet vr-sros VMs to access via tftp
import sys
# import os  # does not work - "no module named 'os'"
from pysros.management import connect


c = connect()
pysros_ds = c.running.get("/nokia-conf:configure/system/name")
print( "/nokia-conf:configure/system/name: %s" % pysros_ds )

print( "sys.version: %s" % sys.version )
# print( "os.environ: {}".format( os.environ ) )

# Be a good netizen
sys.exit( 0 )
