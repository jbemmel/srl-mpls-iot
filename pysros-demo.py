# Map this file to /tftpboot/ for vrnet vr-sros VMs to access via tftp
import sys
from pysros.management import connect


c = connect()
pysros_ds = c.running.get("/nokia-conf:configure/system/name")
print( pysros_ds )

# Be a good netizen
sys.exit( 0 )
