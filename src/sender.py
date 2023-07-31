from network import WLAN, STA_IF
from ubinascii import hexlify, unhexlify
from machine import Pin, reset
from esp32 import NVS
import dht, onewire, ds18x20
import espnow
import time, utime

from configuration_server import serveSetupServer, getStorageVar


# peer = b'\x0c\xdc\x7e\x3c\x1b\xf0'   # MAC address of peer's wifi interface
# peer = b'\xe0\x5a\x1b\x0c\xc6\x1c'   # MAC address of peer's wifi interface
REBOOT_DELAY = 2

class ESPNowClient():
    def __init__(self):
        self.mac = hexlify(WLAN().config('mac'),':').decode()
        self.peer = None
        self.sta = None
        self.client = None

    def enablePowerSavings(self):
        self.sta.config(pm=self.sta.PM_NONE)

    def setup(self):
        self.sta = WLAN(STA_IF)
        self.client = espnow.ESPNow()
        self.sta.active(True)
        self.client.active(True)

        self.enablePowerSavings()

    def addPeer(self, peer):
        print('adding peer: {}'.format(peer))
        peer = unhexlify(peer.replace(':', ''))
        peer = peer.replace(b'Z', b'\x5a')

        self.client.add_peer(peer)      # Must add_peer() before send()
        self.peer = peer

        print('peer added')

    def transmitForAcknowledgement(self):
        # self.sta.active(True)
        ack = self.client.send(self.peer, b'ack {}'.format(self.mac), True)
        return ack

    def transmitEnd(self):
        self.client.send(self.peer, b'end')
        # self.sta.active(False)

    def send(self, msg):
        ack = self.transmitForAcknowledgement()
        if ack is True:
            if type(msg) is not list:
                msg = [msg]

            for m in msg:
                self.client.send(self.peer, str(m))

            self.transmitEnd()
        else:
            print('No ack from gateway')


class BaseSensor():
    def __init__(self, pin, hiveName, interval):
        self.pin = pin
        self.hiveName = hiveName
        self.interval = interval

    @property
    def info(self):
        data = {
            'hive_name': self.hiveName,
            'temperature': "{0:.2f}".format(self.temp),
        }

        if hasattr(self, 'humidity'):
            data['humidity'] = "{0:.2f}".format(self.humidity)

        if hasattr(self, 'pressure'):
            data['pressure'] = "{0:.2f}".format(self.pressure)

        return data


class DHT11Sensor(BaseSensor):
    def __init__(self, pin, hiveName, interval):
        super().__init__(pin, hiveName, interval)
        self.temperature = 0
        self.sensor = dht.DHT11(Pin(self.pin))
        self.lastMeasurement = 0

    def refreshMeasurement(self):
        now = time.time()
        if now - self.lastMeasurement > self.interval:
            self.sensor.measure()
            self.lastMeasurement = now

    @property
    def temp(self):
        self.refreshMeasurement()

        try:
            self.temperature = self.sensor.temperature() or self.temperature
            return self.temperature
        except RuntimeError as error:
            telemetry = {
                'hive_name': self.hiveName,
                'error': str(error),
                'exception': error.__class__.__name__,
                'temperature': self.temperature
            }
            print('DHT sensor got invalid checksum, returning last value.')
            print(telemetry)
            return self.temperature

    @property
    def humidity(self):
        self.refreshMeasurement()
        return self.sensor.humidity()


class DS28B20Sensor(BaseSensor):
    def __init__(self, pin, hiveName, interval):
        super().__init__(pin, hiveName, interval)
        self.temperature = 0
        self.lastMeasurement = 0

        wire = onewire.OneWire(Pin(self.pin))
        self.ds = ds18x20.DS18X20(wire)
        self.sensor = self.ds.scan()[0]

    def refreshMeasurement(self):
        now = time.time()
        if now - self.lastMeasurement > self.interval:
            self.ds.convert_temp()
            self.lastMeasurement = now

    @property
    def temp(self):
        self.refreshMeasurement()
        temp = self.ds.read_temp(self.sensor)
        if temp == 85:
            temp = self.temperature

        self.temperature = temp
        return temp


def reboot(delay = REBOOT_DELAY):
    print (f'Rebooting device in {delay} seconds (Ctrl-C to escape).')
    utime.sleep(delay)
    reset()


def setupAndTransmitTelemetry():
    espNowClient = ESPNowClient()
    espNowClient.setup()
    espNowClient.addPeer(getStorageVar('peer'))
    # net.addPeer(b'\xe0\x5a\x1b\x0c\xc6\x1c')

    dht11Pin = int(getStorageVar('dht11_pin'))
    hive1 = DHT11Sensor(dht11Pin, 'Christine', 1)
    hive1.refreshMeasurement()

    DS28B20Pin = int(getStorageVar('ds28b20_pin'))
    hive2 = DS28B20Sensor(DS28B20Pin, 'Elisabeth', 0.75)
    hive2.refreshMeasurement()

    while True:
        messages = [hive1.info, hive2.info]
        espNowClient.send(messages)

        time.sleep_ms(2 * 1000)


if __name__ == '__main__':
    modeSwitch = Pin(26, Pin.IN, Pin.PULL_UP)
    mode = modeSwitch.value()
    print(mode)

    try:
        if mode == 1:
            print('setupAndTransmitTelemetry')
            setupAndTransmitTelemetry()
        else:
            print('serveSetupServer')
            serveSetupServer()

    except KeyboardInterrupt as err:
        raise err #  use Ctrl-C to exit to micropython repl
    except Exception as err:
        #  all other exceptions cause a reboot
        print ('Error during execution:', err)
        # raise
        reboot()
