# srl-mpls-iot
MPLS interop with SROS and VMX

## Installation steps

* Clone [vrnetlab](https://github.com/hellt/vrnetlab)
* Copy Junos VMX .tgz image to vrnetlab/vmx and run 'make' in that directory -> produces vrnetlab/vr-vmx
* Copy SROS .qcow2 image to vrnetlab/sros and name it like sros-vm-\<release\>.qcow2 -> produces vrnetlab/vr-sros:21.7.R2

[Update Linux kernel to 5.x](https://computingforgeeks.com/install-linux-kernel-5-on-centos-7/)

## Networking
Before using docker-compose to bring up netbox, add the following:
```
networks:
  default:
    driver: bridge
    external: true
    name: clab
```

This ensures the netbox containers are connected to the Containerlab bridge

## Populating Netbox
[Netbox agent](https://github.com/Solvik/netbox-agent) is a Python based tool for automatically populating Netbox with device inventory information.
```
pip3 install netbox-agent
```

To test, register the local server with Netbox (after creating a token):
```
python3 -m netbox_agent.cli --register --netbox.url http://localhost:8000 --netbox.token x --update-all
```

## Adding files to SROS qcow2 image
For example: a license file or Python packages
```
guestfish --rw -a ./sros-vm-21.7.R2.qcow2 -m /dev/sda1 copy-in ./sros.license /
```

# PySROS demo
SROS can now execute Python scripts, for example:
```
A:admin@dcgw1# pyexec tftp://172.31.255.29/pysros-demo.py
dcgw1
```
The setup uses vrnetlab VMs which run a TFTP server inside the container hosting the SROS VM. Each VM has the same IP
