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
---------------------------------------------------------------------------------------------------------------------------------
IPv4 unicast route table of network instance default
---------------------------------------------------------------------------------------------------------------------------------
+-----------------+-------+------------+-------------------+----------+---------+-----------------------+-----------------------+
|   Prefix        |  ID   | Route Type |     Route Owner   |  Metric  |  Pref   |    Next-hop (Type)    |  Next-hop Interface   |
|                 |       |            |                   |          |         |                       |                       |
+=================+=======+============+===================+==========+=========+=======================+=======================+
| 10.0.0.1/32     | 0     | bgp        | bgp_mgr           | 0        | 170     | 172.16.0.14           | None                  |
|                 |       |            |                   |          |         | (indirect)            |                       |
| 10.0.0.2/32     | 0     | bgp        | bgp_mgr           | 0        | 170     | 172.16.0.12           | None                  |
|                 |       |            |                   |          |         | (indirect)            |                       |
| 10.0.0.3/32     | 0     | bgp        | bgp_mgr           | 0        | 170     | 172.16.0.14           | None                  |
|                 |       |            |                   |          |         | (indirect)            |                       |
| 10.0.0.4/32     | 0     | bgp        | bgp_mgr           | 0        | 170     | 172.16.0.12           | None                  |
|                 |       |            |                   |          |         | (indirect)            |                       |
| 10.0.0.5/32     | 0     | bgp        | bgp_mgr           | 0        | 170     | 172.16.0.14           | None                  |
|                 |       |            |                   |          |         | (indirect)            |                       |
| 10.0.0.6/32     | 4     | host       | net_inst_mgr      | 0        | 0       | None (extract)        | None                  |
| 10.0.0.7/32     | 0     | bgp        | bgp_mgr           | 0        | 170     | 172.16.0.12           | None                  |
|                 |       |            |                   |          |         | (indirect)            | None                  |
|                 |       |            |                   |          |         | 172.16.0.14           |                       |
|                 |       |            |                   |          |         | (indirect)            |                       |
| 10.0.0.45/32    | 0     | bgp        | bgp_mgr           | 0        | 170     | 172.16.0.12           | None                  |
|                 |       |            |                   |          |         | (indirect)            | None                  |
|                 |       |            |                   |          |         | 172.16.0.14           |                       |
|                 |       |            |                   |          |         | (indirect)            |                       |
| 10.42.42.0/24   | 0     | bgp        | bgp_mgr           | 0        | 170     | 10.0.0.45 (indirect)  | None                  |
| 172.16.0.12/31  | 2     | local      | net_inst_mgr      | 0        | 0       | 172.16.0.13 (direct)  | ethernet-1/1.0        |
| 172.16.0.13/32  | 2     | host       | net_inst_mgr      | 0        | 0       | None (extract)        | None                  |
| 172.16.0.14/31  | 3     | local      | net_inst_mgr      | 0        | 0       | 172.16.0.15 (direct)  | ethernet-1/2.0        |
| 172.16.0.15/32  | 3     | host       | net_inst_mgr      | 0        | 0       | None (extract)        | None                  |
+-----------------+-------+------------+-------------------+----------+---------+-----------------------+-----------------------+
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
### BGP routes and AS paths
```
A:m# /show network-instance default protocols bgp routes ipv4 summary
-----------------------------------------------------------------------------------------------
Show report for the BGP route table of network-instance "default"
-----------------------------------------------------------------------------------------------
Status codes: u=used, *=valid, >=best, x=stale
Origin codes: i=IGP, e=EGP, ?=incomplete
+--------+-----------------------+--------------+--------+---------+--------------------------+
| Status |        Network        |  Next Hop    |  MED   | LocPref |  AS Path Val             |
|        |                       |              |        |         |                          |
+========+=======================+==============+========+=========+==========================+
| *      | 10.0.0.1/32           | 172.16.0.12  | -      | 100     | [65004, 65005, 65001] i  |
| u*>    | 10.0.0.1/32           | 172.16.0.14  | -      | 100     | [65005, 65001] i         |
| u*>    | 10.0.0.2/32           | 172.16.0.12  | -      | 100     | [65004, 65002] i         |
| *      | 10.0.0.2/32           | 172.16.0.14  | -      | 100     | [65005, 65003, 65002] i  |
| *      | 10.0.0.3/32           | 172.16.0.12  | -      | 100     | [65004, 65002, 65003] i  |
| u*>    | 10.0.0.3/32           | 172.16.0.14  | -      | 100     | [65005, 65003] i         |
| u*>    | 10.0.0.4/32           | 172.16.0.12  | -      | 100     | [65004] i                |
| *      | 10.0.0.4/32           | 172.16.0.14  | -      | 100     | [65005, 65004] i         |
| *      | 10.0.0.5/32           | 172.16.0.12  | -      | 100     | [65004, 65005] i         |
| u*>    | 10.0.0.5/32           | 172.16.0.14  | -      | 100     | [65005] i                |
| u*>    | 10.0.0.6/32           | 0.0.0.0      | -      | 100     |  i                       |
|        | 10.0.0.6/32           | 172.16.0.12  | -      | 100     | [65004, 65006] i         |
|        | 10.0.0.6/32           | 172.16.0.14  | -      | 100     | [65005, 65006] i         |
| u*>    | 10.0.0.7/32           | 172.16.0.12  | -      | 100     | [65004, 65100] i         |
| u*>    | 10.0.0.7/32           | 172.16.0.14  | -      | 100     | [65005, 65100] i         |
| u*>    | 10.0.0.45/32          | 172.16.0.12  | -      | 100     | [65004, 64999] i         | <= anycast nexthop #1
| u*>    | 10.0.0.45/32          | 172.16.0.14  | -      | 100     | [65005, 64999] i         | <= anycast nexthop #2
| u*>    | 10.42.42.0/24         | 10.0.0.45    | -      | 100     | [65001, 65004, 64999] ?  | <= anycast route
| u*>    | 172.16.0.12/31        | 0.0.0.0      | -      | 100     |  i                       |
| u*>    | 172.16.0.14/31        | 0.0.0.0      | -      | 100     |  i                       |
+--------+-----------------------+--------------+--------+---------+--------------------------+
20 received BGP routes: 13 used, 18 valid, 0 stale
13 available destinations: 7 with ECMP multipaths
```
Note the 'invalid' routes to 10.0.0.6/32 here, which include the node's own AS in their AS path. These could be filtered out at the source (this looks like an obvious optimization, however I am not aware of any easy knob to apply this other than spelling out the peer AS to filter out for each peer). Now implemented in the SROS policies

### Route Reflector view
At the Route Reflector (rr) node, the routes look like this:
```
A:rr# /show network-instance default protocols bgp neighbor 172.16.0.8 received-routes ipv4
-------------------------------------------------------------------------------------------------------------------
Peer        : 172.16.0.8, remote AS: 65003, local AS: 65001
Type        : static
Description : None
Group       : underlay
-------------------------------------------------------------------------------------------------------------------
Status codes: u=used, *=valid, >=best, x=stale
Origin codes: i=IGP, e=EGP, ?=incomplete
+-----------------------------------------------------------------------------------------------------------------+
|  Status      Network             Next Hop          MED      LocPref           AsPath              Origin        |
+=================================================================================================================+
|    u*>      10.0.0.2/32          172.16.0.8         -         100        [65003, 65002]              i          |
|    u*>      10.0.0.3/32          172.16.0.8         -         100        [65003]                     i          |
|     *       10.0.0.4/32          172.16.0.8         -         100        [65003, 65002, 65004]       i          |
|     *       10.0.0.5/32          172.16.0.8         -         100        [65003, 65005]              i          |
|     *       10.0.0.6/32          172.16.0.8         -         100        [65003, 65005, 65006]       i          |
|     *       10.0.0.7/32          172.16.0.8         -         100        [65003, 65005, 65100]       i          |
|     *       10.0.0.45/32         172.16.0.8         -         100        [65003, 65005, 64999]       i          |
+-----------------------------------------------------------------------------------------------------------------+
7 received BGP routes : 2 used 7 valid
-------------------------------------------------------------------------------------------------------------------
--{ + running }--[  ]--                                                                                             
A:rr# /show network-instance default protocols bgp neighbor 172.16.0.10 received-routes ipv4                        
-------------------------------------------------------------------------------------------------------------------
Peer        : 172.16.0.10, remote AS: 65005, local AS: 65001
Type        : static
Description : None
Group       : underlay
-------------------------------------------------------------------------------------------------------------------
Status codes: u=used, *=valid, >=best, x=stale
Origin codes: i=IGP, e=EGP, ?=incomplete
+-----------------------------------------------------------------------------------------------------------------+
|  Status      Network             Next Hop          MED      LocPref           AsPath              Origin        |
+=================================================================================================================+
|     *       10.0.0.2/32          172.16.0.10        -         100        [65005, 65003, 65002]       i          |
|     *       10.0.0.3/32          172.16.0.10        -         100        [65005, 65003]              i          |
|    u*>      10.0.0.4/32          172.16.0.10        -         100        [65005, 65004]              i          |
|    u*>      10.0.0.5/32          172.16.0.10        -         100        [65005]                     i          |
|    u*>      10.0.0.6/32          172.16.0.10        -         100        [65005, 65006]              i          |
|    u*>      10.0.0.7/32          172.16.0.10        -         100        [65005, 65100]              i          |
|    u*>      10.0.0.45/32         172.16.0.10        -         100        [65005, 64999]              i          |  <= used, shorter AS path
+-----------------------------------------------------------------------------------------------------------------+
7 received BGP routes : 5 used 7 valid
```
Note the difference in AS path length towards the nexthop 10.0.0.45/32; the RR only installs a single next hop (d)
