# srl-mpls-iot
MPLS interop with SROS and VMX

## Installation steps

* Clone [vrnetlab](https://github.com/hellt/vrnetlab)
* Copy Junos VMX .tgz image to vrnetlab/vmx and run 'make' in that directory -> produces vrnetlab/vr-vmx
* Copy SROS .qcow2 image to vrnetlab/sros and name it like sros-vm-\<release\>.qcow2 -> produces vrnetlab/vr-sros:21.7.R2

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
