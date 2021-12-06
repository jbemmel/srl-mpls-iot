# Automating BGP anycast 🔨 (one next-hop to rule them all 💍)

Ivan was [at it again](https://blog.ipspace.net/2021/12/bgp-multipath-addpath.html) last week, taking his [Netsim tools](https://github.com/ipspace/netsim-tools) to task on a set of virtual nodes to solve a particular issue with sub-optimal routing using the 'addpath' capability ([RFC7911](https://datatracker.ietf.org/doc/html/rfc7911)).

Having read [this](https://blog.ipspace.net/2021/11/anycast-mpls.html) made me wonder if there wasn't another simpler, multi-vendor solution to be explored, one that doesn't require exotic BGP features or prolonged maintenance windows. One that doesn't depend on scarce engineering resources, or hard to get vendor images.

![plot](BGP_Anycast_lab.PNG)

# Installation
Prerequisites: Docker and Containerlab installed

SROS image - see [build instructions](https://containerlab.srlinux.dev/manual/vrnetlab/)
```
git checkout https://github.com/jbemmel/srl-mpls-iot.git
cd srl-mpls-iot/labs/sr-bgp-anycast
sudo containerlab deploy -t ./sr-bgp-anycast.lab
```
Wait until the nodes have booted, then:
```
sudo containerlab config -t ./sr-bgp-anycast.lab -l sr-bgp-anycast -p .
```

## BGP Anycast
Conceptually, an anycast address represents a set of equivalent destinations. It is commonly used in load-balancers and DNS services to direct clients to the 'closest' resource that can satisfy their request. In Ivan's case, if the problem is that the Route Reflector can only advertise one (1) best path per prefix, a potential solution is to use an anycast IP as that single next hop associated with that prefix. That way, nodes in the network can figure out what their locally preferred set of next hops might be.

None of this is particularly new; this [SROS 9.0R1 Advanced Solution Guide from 2011](https://documentation.nokia.com/html/0_add-h-f/93-0267-HTML/7X50_Advanced_Configuration_Guide/BGP_anycast.pdf) described it in great detail for example. That feature applies to MPLS networks with BGP labels and what have you; it creates an active/standby pair of anycast addresses for additional redundancy (which would lead us back to the maximum 1 best path issue...).

## Sample routing table
On SRL node m:
```
A:m# show route-table ipv4-unicast summary                                                                                                                                                                         
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
IPv4 unicast route table of network instance default
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
+-----------------+-------+------------+----------------------+----------------------+----------+---------+-----------------------+-----------------------+
|   Prefix        |  ID   | Route Type |     Route Owner      |      Best/Fib-       |  Metric  |  Pref   |    Next-hop (Type)    |  Next-hop Interface   |
|                 |       |            |                      |     status(slot)     |          |         |                       |                       |
+=================+=======+============+======================+======================+==========+=========+=======================+=======================+
| 10.0.0.1/32     | 0     | bgp        | bgp_mgr              | True/success         | 0        | 170     | 172.16.0.14           | None                  |
|                 |       |            |                      |                      |          |         | (indirect)            |                       |
| 10.0.0.2/32     | 0     | bgp        | bgp_mgr              | True/success         | 0        | 170     | 172.16.0.12           | None                  |
|                 |       |            |                      |                      |          |         | (indirect)            |                       |
| 10.0.0.3/32     | 0     | bgp        | bgp_mgr              | True/success         | 0        | 170     | 172.16.0.14           | None                  |
|                 |       |            |                      |                      |          |         | (indirect)            |                       |
| 10.0.0.4/32     | 0     | bgp        | bgp_mgr              | True/success         | 0        | 170     | 172.16.0.12           | None                  |
|                 |       |            |                      |                      |          |         | (indirect)            |                       |
| 10.0.0.5/32     | 0     | bgp        | bgp_mgr              | True/success         | 0        | 170     | 172.16.0.14           | None                  |
|                 |       |            |                      |                      |          |         | (indirect)            |                       |
| 10.0.0.6/32     | 4     | host       | net_inst_mgr         | True/success         | 0        | 0       | None (extract)        | None                  |
| 10.0.0.7/32     | 0     | bgp        | bgp_mgr              | True/success         | 0        | 170     | 172.16.0.12           | None                  |
|                 |       |            |                      |                      |          |         | (indirect)            | None                  |
|                 |       |            |                      |                      |          |         | 172.16.0.14           |                       |
|                 |       |            |                      |                      |          |         | (indirect)            |                       |
| 10.0.0.45/32    | 0     | bgp        | bgp_mgr              | True/success         | 0        | 170     | 172.16.0.12           | None                  |
|                 |       |            |                      |                      |          |         | (indirect)            | None                  |
|                 |       |            |                      |                      |          |         | 172.16.0.14           |                       |
|                 |       |            |                      |                      |          |         | (indirect)            |                       |
| 10.42.42.0/24   | 0     | bgp        | bgp_mgr              | True/success         | 0        | 170     | 10.0.0.45 (indirect)  | None                  |
| 172.16.0.12/31  | 2     | local      | net_inst_mgr         | True/success         | 0        | 0       | 172.16.0.13 (direct)  | ethernet-1/1.0        |
| 172.16.0.13/32  | 2     | host       | net_inst_mgr         | True/success         | 0        | 0       | None (extract)        | None                  |
| 172.16.0.14/31  | 3     | local      | net_inst_mgr         | True/success         | 0        | 0       | 172.16.0.15 (direct)  | ethernet-1/2.0        |
| 172.16.0.15/32  | 3     | host       | net_inst_mgr         | True/success         | 0        | 0       | None (extract)        | None                  |
+-----------------+-------+------------+----------------------+----------------------+----------+---------+-----------------------+-----------------------+
IPv4 routes total                    : 13
IPv4 prefixes with active routes     : 13
IPv4 prefixes with active ECMP routes: 2

--{ + running }--[ network-instance default ]--                                                                                                                                                                    
A:m# ping 10.42.42.0 -I 10.0.0.6 -c3                                                                                                                                                                               
Using network instance default
PING 10.42.42.0 (10.42.42.0) from 10.0.0.6 : 56(84) bytes of data.
64 bytes from 10.42.42.0: icmp_seq=1 ttl=63 time=17.1 ms
64 bytes from 10.42.42.0: icmp_seq=2 ttl=63 time=9.87 ms
64 bytes from 10.42.42.0: icmp_seq=3 ttl=63 time=11.6 ms

--- 10.42.42.0 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2004ms
rtt min/avg/max/mdev = 9.870/12.863/17.084/3.071 ms
--{ + running }--[ network-instance default ]--
```
