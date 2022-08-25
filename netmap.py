from mininet.cli import CLI
from mininet.net import Mininet
from mininet.node import OVSBridge
from mininet.topo import Topo
from mininet.log import info, error, setLogLevel

class MyNetwork(Topo):
    def build(self):
        r0 = self.addHost('r0', ip='192.168.10.1/24')
        r1 = self.addHost('r1', ip='192.168.10.1/24')
        s0 = self.addSwitch('s0')
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')

        self.addLink(s0,r0)
        self.addLink(s1,r1)

        for i in range(3):
            host = self.addHost(f'r0h{i}', ip=f'192.168.10.{10+i}/24')
            self.addLink(s0, host)
            host = self.addHost(f'r1h{i}', ip=f'192.168.10.{10+i}/24')
            self.addLink(s1, host)

        self.addLink(r0,s2, params1=dict(ip='192.168.20.1/24'))
        self.addLink(r1,s2, params1=dict(ip='192.168.20.2/24'))

        nas = self.addHost('nas', ip='192.168.20.10/24')
        self.addLink(nas,s2)


topos = {"mynet": MyNetwork}

if __name__ == '__main__':
    setLogLevel("info")

    topo = MyNetwork()
    net = Mininet(topo=topo, switch=OVSBridge)
    net.start()

    try:
        r0 = net.nameToNode['r0']
        r1 = net.nameToNode['r1']

        for router in range(2):
            for host in range(3):
                host = net.nameToNode[f'r{router}h{host}']
                host.cmd('ip route add default via 192.168.10.1')

        r0.cmd('ip route add 192.168.30.0/24 via 192.168.20.2')
        r0.cmd('iptables -t nat -A PREROUTING -d 192.168.30.0/24 -i r0-eth1 -j NETMAP --to 192.168.10.0/24')
        r0.cmd('iptables -t nat -A POSTROUTING -o r0-eth1 -j MASQUERADE')

        r1.cmd('ip route add 192.168.30.0/24 via 192.168.20.1')
        r1.cmd('iptables -t nat -A PREROUTING -d 192.168.30.0/24 -i r1-eth1 -j NETMAP --to 192.168.10.0/24')
        r1.cmd('iptables -t nat -A POSTROUTING -o r1-eth1 -j MASQUERADE')


        CLI(net)
    finally:
        net.stop()
