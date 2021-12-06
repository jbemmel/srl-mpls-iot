# Automating BGP anycast 🔨

Ivan was [at it again](https://blog.ipspace.net/2021/12/bgp-multipath-addpath.html) last week, taking his Netsim tools to task on a set of virtual nodes to demonstrate the 'addpath' capability.

Having read [this](https://blog.ipspace.net/2021/11/anycast-mpls.html) and finding [that (2011) from SROS 9.0R1](https://documentation.nokia.com/html/0_add-h-f/93-0267-HTML/7X50_Advanced_Configuration_Guide/BGP_anycast.pdf) made me wonder if there wasn't another simpler, multi-vendor solution to be explored, one that doesn't require exotic BGP features or prolonged maintenance windows. One that doesn't depend on scarce engineering resources, or hard to get vendor images.

## BGP Anycast
Conceptually, anycast accomodates equivalence of destinations.
