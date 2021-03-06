set /system gnmi-server unix-socket admin-state enable
set /auto-config-agent gateway ipv4 10.0.0.1/24 location spine
set /auto-config-agent lacp active # reload-delay-secs 0
set /auto-config-agent igp ospf evpn model symmetric-irb auto-lags encoded-ipv6 bgp-peering ipv4 overlay-as 65000 route-reflector spine

# Allow NetBox API commands over ipv4
/acl cpm-filter ipv4-filter entry 365 match protocol tcp destination-port value 8000 operator eq
/acl cpm-filter ipv4-filter entry 365 action accept
/acl cpm-filter ipv4-filter entry 366 match protocol tcp source-port value 8000 operator eq
/acl cpm-filter ipv4-filter entry 366 action accept

/netbox-agent
