import subprocess
import sys

from mininet.cli import CLI
from mininet.log import info, error, setLogLevel
from mininet.net import Mininet
from mininet.node import OVSBridge

import pvtnet


class CommandFailedError(Exception):
    """Used to signal a failed command execution by the `must()` wrapper
    function"""

    def __init__(self, *args, stdout=None, stderr=None, ret=None):
        self.stdout = stdout
        self.stderr = stderr
        self.ret = ret
        super().__init__(*args)


def must(out, err, ret):
    """This is a wrapper for the mininet `pexec` function that will raise a
    CommandFailedError exception if a command returns a nonzero exit code"""

    if ret != 0:
        raise CommandFailedError(stdout=out, stderr=err, ret=ret)

    return out, err


def main():
    ip_forward = subprocess.check_output("sysctl net.ipv4.ip_forward", shell=True)
    if ip_forward.decode().strip().split()[-1] != "1":
        info("enabling ip forwarding\n")
        subprocess.check_call("sysctl -w net.ipv4.ip_forward=1", shell=True)

    net = Mininet(topo=pvtnet.PvtNet(), switch=OVSBridge)
    net.start()

    try:
        servera = net.nameToNode["servera"]
        serverb = net.nameToNode["serverb"]
        devx = net.nameToNode["devx"]
        devy = net.nameToNode["devy"]

        # pylint: disable=invalid-name
        r0 = net.nameToNode["r0"]

        servera_wg0_addr = next(net.topo.vpn_addr)
        serverb_wg0_addr = next(net.topo.vpn_addr)

        info("configuring routes on serverb devices\n")
        for host in [serverb, devx, devy]:
            must(*host.pexec("ip route add default via 192.168.27.1", shell=True))

        info("configuring masquerading on r0\n")
        must(
            *r0.pexec(
                "iptables -t nat -A POSTROUTING -s 192.168.27.0/24 -j MASQUERADE",
                shell=True,
            )
        )

        info("creating wireguard devices\n")
        for host in [servera, serverb]:
            must(*host.pexec("ip link add wg0 type wireguard", shell=True))

        info("creating private keys\n")
        servera_pub = (
            subprocess.check_output(
                "wg genkey | tee servera.private | wg pubkey", shell=True
            )
            .decode()
            .strip()
        )
        serverb_pub = (
            subprocess.check_output(
                "wg genkey | tee serverb.private | wg pubkey", shell=True
            )
            .decode()
            .strip()
        )

        info("configuring vpn\n")

        must(*servera.pexec(f"ip addr add {servera_wg0_addr} dev wg0", shell=True))
        must(
            *servera.pexec(
                "wg set wg0 listen-port 51820 private-key servera.private "
                f'peer "{serverb_pub}" '
                f'allowed-ips "{net.topo.serverb_net},{net.topo.vpn_net}"',
                shell=True,
            )
        )
        must(*servera.pexec("ip link set wg0 up", shell=True))

        must(*serverb.pexec(f"ip addr add {serverb_wg0_addr} dev wg0", shell=True))
        must(
            *serverb.pexec(
                "wg set wg0 listen-port 51820 private-key serverb.private "
                f'peer "{servera_pub}" '
                f'allowed-ips "{net.topo.servera_net},{net.topo.vpn_net}" '
                f'endpoint "{servera.intfs[1].ip.split("/")[0]}:51820"',
                shell=True,
            )
        )
        must(*serverb.pexec("ip link set wg0 up", shell=True))

        info("configuring vpn routes\n")
        must(
            *servera.pexec(
                f"ip route add {net.topo.serverb_net} via {servera_wg0_addr.split('/')[0]}",
                shell=True,
            )
        )
        must(
            *serverb.pexec(
                f"ip route add {net.topo.servera_net} via {serverb_wg0_addr.split('/')[0]}",
                shell=True,
            )
        )
        must(
            *r0.pexec(
                f"ip route add {net.topo.servera_net} via {serverb.intfs[0].ip.split('/')[0]} && "
                f"ip route add {net.topo.vpn_net} via {serverb.intfs[0].ip.split('/')[0]}",
                shell=True,
            )
        )

        info("prime vpn connection\n")
        serverb.cmd(
            f"until ping -c1 {servera.intfs[0].ip.split('/')[0]}; do sleep 1; done"
        )

        CLI(net)
    except CommandFailedError as err:
        error(f"command failed with status {err.ret}: {err.stderr}")
    finally:
        net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    main()
