# HW Architecture & System Configuration

![HW architecture](architecture-hw.svg)

Power for the upper part is provided by the **NB Air 5000** power bank connected via **USB-C**. The 5000 mAh capacity is sufficient for measurement purposes. All devices on the drone are powered from this branch.

One power branch goes through the **LM2577 step-up converter**, which increases the voltage to **48 V** for the **PoE injector**. The **Teltonika OTD 500** is powered via PoE.

The second branch goes through the **LM2596 step-down converter**, which reduces the voltage to **5.1 V** for powering the **Raspberry Pi 4B**.

The **Raspberry Pi 4B** is connected to the **Teltonika OTD 500** via a UTP cable through the PoE injector.

Teltonika provides connectivity to the **4G/5G** network using two SIM cards and acts as the default gateway for the `10.0.2.0/24` network.

On the ground station there is a **Raspberry Pi 5**, connected to a **Alfa AWUS1900 Wi-Fi adapter**, which provides AP mode for the Wi-Fi link to the drone. The user device is connected to the ground station local network as a **DHCP client**.

---

## Important

- **Upper device (drone)** – Raspberry Pi 4B in client mode, LTE/5G Teltonika router, PoE power
- **Lower device (ground station)** – Raspberry Pi 5 with USB Wi-Fi adapter in AP mode

Communication between the ground station and the drone is done via Wi-Fi 802.11ac.

---

## IP Addressing

| IP Address | Interface | Device | Description |
|----------|----------|----------|-------|
| 10.0.0.1 | eth0 | Ground RPi | Local network for users with DHCP server |
| 10.0.1.1 | wlan1 | Ground RPi | Access point for Wi-Fi link (AP) |
| 10.0.1.2 | wlan0 | Drone RPi | Wi-Fi client |
| 10.0.2.1 | eth0 | Drone RPi | Internal drone network |
| 10.0.2.2 | eth0 | Teltonika | LTE/5G router |

All network interfaces are managed by systemd-networkd, except for eth0 on the Ground RPi, which is managed by NetworkManager.

---

## Wi-Fi connection on ground station

Wi-Fi connection configuration is handled by systemd-networkd on the wlan1 interface of ground RPi.

Configuration file (`/etc/systemd/network/10-wlan1.network`):

```conf
[Match]
Name=wlan1

[Network]
Address=10.0.1.1/24

[Route]
Destination=10.0.2.0/24
Gateway=10.0.1.2
```

---

## DHCP Configuration

Configuration of **eth0** on the ground station (**Netplan + NetworkManager**):

```yaml
network:
  version: 2
  ethernets:
    NM-50571c25-07a1-4074-9cbf-496e484c273f:
      renderer: NetworkManager
      match:
        name: "eth0"
      addresses:
      - "10.0.0.1/24"
      dhcp6: true
      wakeonlan: true
      networkmanager:
        uuid: "50571c25-07a1-4074-9cbf-496e484c273f"
        name: "eth0-internal"
        passthrough:
          connection.timestamp: "1764594033"
          ethernet._: ""
          ipv6.addr-gen-mode: "default"
          ipv6.ip6-privacy: "-1"
          proxy._: ""
```


On the ground station, the DHCP server is handled by dnsmasq. DHCP is running on the eth0 (10.0.0.1) interface.
Configuration (`/etc/dnsmasq.conf`):

```conf
interface=eth0 # listen only on eth0

dhcp-range=10.0.0.100,10.0.0.200,255.255.255.0,24h # address range and lease time

dhcp-option=3,10.0.0.1 # default gateway

dhcp-option=6,8.8.8.8  # DNS server

no-dhcp-interface=wlan1 # do not send DHCP on other interfaces
no-dhcp-interface=eth1
```

---

## AP Configuration (Ground Station RPi)

The AP runs on the wlan1 interface on the RPi 5 using hostapd. The AP is used to connect the RPi client on the drone.

Configuration (`/etc/hostapd/hostapd.conf`):

```conf
# AP interface
interface=wlan1            # interface on which hostapd runs
driver=nl80211             # used driver
ssid=Scandrone-Base
country_code=CZ

# Security
wpa=2                      # WPA2 enabled
wpa_passphrase=...
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP          # AES (CCMP) encryption
auth_algs=1
wds_sta=1

# Radio configuration on 5 GHz
hw_mode=a                  # 5 GHz band
channel=44                 # used channel
ieee80211ac=1              # 802.11ac standard
vht_oper_centr_freq_seg0_idx=46
ht_capab=[HT40+][SHORT-GI-40][TX-STBC][RX-STBC1]
wmm_enabled=1
```

---

## Client Connection (Drone RPi)

Client connection configuration is handled by systemd-networkd on the wlan0 interface.

Configuration file (`/etc/systemd/network/08-wifi.network`):

```conf
[Match]
Name=wlan0

[Network]
Address=10.0.1.2/24 # wlan0 address on Wi-Fi link
DHCP=no
IPv4Forwarding=yes # enable forwarding
IPv4ProxyARP=no

[Route]
Destination = 10.0.0.0/24
Gateway=10.0.1.1 # gateway to the ground station network
```
---

## Static Routes

### Ground Station

- `10.0.2.0/24 via 10.0.1.2 dev wlan1` – static route to the internal drone network via the Wi-Fi client interface (10.0.1.2)

### Drone

- `10.0.0.0/24 via 10.0.1.1 dev wlan0` – static route to the internal ground station network via interface on the ground station (10.0.1.1)
