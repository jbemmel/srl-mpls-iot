# Map this file to /tftpboot/ for vrnet vr-sros VMs to access via tftp
import sys, os
from pysros.management import connect


c = connect()
pysros_ds = c.running.get("/nokia-conf:configure/system/name")
print( f"/nokia-conf:configure/system/name: {pysros_ds}" )

print( f"os.environ: {os.environ}" )

# Be a good netizen
sys.exit( 0 )
