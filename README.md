# Hivemonitor ESP32 Firmware

Firmware for running Hivemonitor on ESP32 microcontrollers.

Complemetary hivemonitor repositories:
- [Hive monitor webpage](https://github.com/kevinmidboe/hivemonitor)
- [Hive monitor ESP32 PCB design](https://github.com/kevinmidboe/hivemonitor-pcb)

# Architecture

![hivemonitor architecture drawing](https://github.com/KevinMidboe/hivemonitor-esp32-firmware/assets/2287769/c40512e5-9f31-4aea-a8db-e92646c51903)

# Operating modes

## Setup mode
Both types of devices acting as `sending` and `gateway` have a operating and setup mode. By using the on-board switch labeled "MODE" the esp32 will boot up in setup mode and be available as a WiFi hotspot named `ESP-AP-*`. View [setup section](#setup) below.

## Sender device
Devices acting as sensor have weight, temperature and humidity sensors connected that will be read and broadcasted using ESP-NOW peer-to-peer protocol. 

## Gateway device
Device acting as receiver will be simultaneously be listening for messages broadcasted to it's MAC address using ESP-NOW & connected to WiFi to send MQTT messages to a broker. 

# Installation

Clone repository and navigate into folder:
```bash
git clone https://github.com/kevinmidboe/hivemonitor-esp32-firmware
cd hivemonitor-esp32-firmware
```

## TL;DR

Flash microcontroller:
```bash
wget https://raw.githubusercontent.com/glenn20/micropython-espnow-images/main/20230427-v1.20.0-espnow-2-gcc4c716f6/firmware-esp32-GENERIC.bin > firmware-esp32-espnow.bin
make flash file=firmware-esp32-espnow.bin device=/dev/tty.usbserial-02899247
```
Upload source code:
```bash
make sender device=/dev/tty.usbserial-02899247
# or
make gateway device=/dev/tty.usbserial-02899247
```

## Flashing firmware
The current supported flashing tool for micropython firmware is esptool.py. You can find this tool here: https://github.com/espressif/esptool/, or install it using pip:

```bash
pip install esptool
```

Download firmware from [supported firmware linked below](#firmware-sources) or compile required micropython with libraries listed below:
- espnow
- usocket
- umqtt.simple

Plug esp32 into computers USB and find it's connected TTY port with:

```bash
ls -l /dev/tty.*
```

Erase the existing firmware and then deploy the new firmware using:
```bash
make flash device=/dev/tty.usbserial-02899247
```

## Uploading application source files

For uploading source files we can use adafruit ampy CLI found at https://github.com/espressif/esptool, or installed with pip:

```bash
pip install adafruit-ampy
```

Upload all files for ESP32 that will be acting as a `gateway` by running:

```bash
make gateway
```

Upload all files for ESP32 that will be acting as a `sensor reader & sender` by running:

```bash
make sender
```

# Setup

After uploading source files, use the on-board MODE switch to side marked "Setup" device to boot board into setup mode. Inputs will b based on if device is setup as `sender` or `gateway`.

After setting mode switch and resetting the controller will be discoverable as a WiFi access point serving a configuration page.
 1. Connect to WiFi network prefixed with `ESP-AP-`
 2. Open browser to http://192.168.0.4

Below shows screenshots of gateway device in setup mode:

![Hive monitor setup site, 3 pages](https://github.com/KevinMidboe/hivemonitor-esp32-firmware/assets/2287769/3e80fa3d-7b5e-4296-89a0-a3d42351ddf3)

🎉 Setup completed!  
When both a sender and gateway is setup MQTT messages should start reaching broker.

# ESP32

## Deep sleep
asdf

## Networking
There are two WiFi interfaces, STA mode is workstation mode (ESP32 is connected to the router)，AP mode provides access services (other devices connected to ESP32).


The ESP32 does not have two antennas, but we can run two interfaces `STA` & `AP`. The drawback of this is that since we only have one antenna we need to make sure the sending and receiving devices are both broadcasting on same channel. In a sitation where your WiFi access point might be brodcasting on channel e.g. 6 the ESP32 connects over WiFi on this channel. The ESP32 sending sensor data therefor needs to be broadcasting data over ESP-NOW on same channel.

## Firmware sources

| mpy version | espnow | mqtt* | socket | source                                                                                                                                                                  |
|-------------|--------|-------|--------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| v1.20       | ✅    | ✅   | ✅    | [github.com/glenn20/micropython-espnow/20230427-v1.20.0-espnow/firmware.bin](https://github.com/glenn20/micropython-espnow-images/blob/main/20230427-v1.20.0-espnow-2-gcc4c716f6/firmware-esp32-GENERIC.bin) |
| v1.19       | ✅    | ✅   | ✅    | [github.com/glenn20/micropython-espnow/20220709-v1.19.1-espnow/firmware.bin](https://github.com/glenn20/micropython-espnow-images/blob/main/20220709_espnow-g20-v1.19.1-espnow-6-g44f65965b/firmware-esp32-GENERIC.bin) |

