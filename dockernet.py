from mininet.cli import CLI
from mininet.net import Mininet
from mininet.node import OVSBridge
from mininet.topo import Topo
from mininet.log import info, error, setLogLevel

class DockerNet(Topo):
    def build(self):
        s0 = self.addSwitch('s0')
        s1 = self.addSwitch('s1')

        router = self.addHost('router', ip='10.10.60.1/24')
        ctrhost = self.addHost('ctrhost', ip='10.10.60.41/24')
        otherhost = self.addHost('otherhost', ip='10.10.60.20/24')
        ctr1 = self.addHost('ctr1', ip='10.60.0.2/16')

        for host in [router, ctrhost, otherhost]:
            self.addLink(host, s1)

        self.addLink(ctrhost,s0,params1=dict(ip='10.60.0.1/16'))
        self.addLink(ctr1,s0)


topos = {"docker": DockerNet}

if __name__ == '__main__':
    setLogLevel("info")

    topo = DockerNet()
    net = Mininet(topo=topo, switch=OVSBridge)
    net.start()

    try:
        router = net.nameToNode['router']
        ctrhost = net.nameToNode['ctrhost']
        ctr1 = net.nameToNode['ctr1']
        otherhost = net.nameToNode['otherhost']

        info("Adding routes\n")
        for host in [ctrhost, otherhost]:
            host.cmd("ip route add default via 10.10.60.1")
        ctr1.cmd("ip route add default via 10.60.0.1")

        router.cmd("ip route add 10.60.0.0/16 via 10.10.60.41")

        CLI(net)
    finally:
        net.stop()
