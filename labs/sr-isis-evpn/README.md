# SROS SR/MPLS with ISIS and EVPN

This is an initial lab to try out SR/MPLS with ISIS and EVPN, using Containerlab

## Deploy lab
```
sudo containerlab deploy -t sr-isis-evpn.lab --reconfigure
```

## Configure nodes using templates
```
sudo containerlab config -t ./sr-isis-evpn.lab -p . -l sr-isis-evpn
```
