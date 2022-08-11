from mininet.topo import Topo

import netaddr


class UsefulIPNetwork(netaddr.IPNetwork):
    def iter_hosts(self, start=None, end=None):
        first = self.first + start if start else self.first + 1
        last = self.first + end if end else self.last - 1
        addrs = netaddr.ip.iter_iprange(
            netaddr.IPAddress(first), netaddr.IPAddress(last)
        )

        for addr in addrs:
            yield f"{addr}/{self.prefixlen}"

    def __getitem__(self, k):
        addr = super().__getitem__(k)
        return f"{addr}/{self.prefixlen}"


class PvtNet(Topo):
    public_net_cidr = "10.100.10.0/28"
    servera_net_cidr = "172.16.10.0/24"
    serverb_net_cidr = "192.168.27.0/24"
    vpn_net_cidr = "10.200.10.0/28"

    def build(self):
        self.public_net = public_net = UsefulIPNetwork(self.public_net_cidr)
        self.servera_net = servera_net = UsefulIPNetwork(self.servera_net_cidr)
        self.serverb_net = serverb_net = UsefulIPNetwork(self.serverb_net_cidr)
        self.vpn_net = vpn_net = UsefulIPNetwork(self.vpn_net_cidr)

        self.publioc_addr = public_addr = public_net.iter_hosts(start=10)
        self.servera_addr = servera_addr = servera_net.iter_hosts(start=10)
        self.serverb_addr = serverb_addr = serverb_net.iter_hosts(start=10)
        self.vpn_addr = vpn_addr = vpn_net.iter_hosts(start=10)

        vm1 = self.addHost("vm1", ip=next(servera_addr))
        servera = self.addHost("servera", ip=servera_net[1])
        serverb = self.addHost("serverb", ip=next(serverb_addr))
        r0 = self.addHost("r0", ip=serverb_net[1])
        devx = self.addHost("devx", ip=next(serverb_addr))
        devy = self.addHost("devy", ip=next(serverb_addr))

        sw0 = self.addSwitch("sw0")
        sw1 = self.addSwitch("sw1")

        self.addLink(vm1, sw0)
        self.addLink(servera, sw0)
        self.addLink(sw1, r0)
        self.addLink(
            servera,
            r0,
            params1={"ip": next(public_addr)},
            params2={"ip": next(public_addr)},
        )
        self.addLink(serverb, sw1)
        self.addLink(devx, sw1)
        self.addLink(devy, sw1)


topos = {"pvtnet": PvtNet}
