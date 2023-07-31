import network, time, utime, json, machine, esp32, ntptime
import espnow
from machine import Pin, ADC
from umqtt.simple import MQTTClient
from ubinascii import b2a_base64

from configuration_server import serveSetupServer, getStorageVar

REBOOT_DELAY = 2
wifiChannel = -1
# BASE_TOPIC = getStorageVar('mqtt_topic')


class Wifi():
    def __init__(self):
        self.sta = network.WLAN(network.STA_IF)
        self.channel = -1

    # The power saving mode causes the device to turn off the radio
    # periodically (typically for hundreds of milliseconds), making
    # it unreliable in receiving
    def disablePowerSavings(self):
        self.sta.config(pm=self.sta.PM_NONE)

    def setChannel(self):
        global wifiChannel
        self.channel = self.sta.config("channel")
        wifiChannel = self.channel
        print("Proxy running on channel:", self.channel)

    def connect(self, ssid, password):
        self.sta.active(True)
        self.sta.connect(ssid, password)
        while not self.sta.isconnected():  # Wait until connected...
            time.sleep(0.5)
            print('waiting to connect to wifi...')

        self.sta.config(pm=self.sta.PM_NONE)
        print('Connected to wifi "%s"' % ssid)

        self.disablePowerSavings()
        self.setChannel()


class ESPNowServer():
    def __init__(self):
        self.ap = network.WLAN(network.AP_IF)
        self.server = None
        self.mqttClient = None

    def setup(self):
        self.server = espnow.ESPNow()
        self.server.active(True)
        print("Successtully activate ESP now on AP antenna")

    def receive(self, mqttClient):
        count = 0
        mqttClient.publishGatewayStatus()

        while True:
            # TODO change to irecv, bytearray instead of bytestring
            peer, msg = self.server.recv()
            if msg is not None and msg not in [b'end'] and 'ack' not in msg:
                payload = parse_json(msg.decode('utf-8'))
                hiveName = payload['hive_name']

                mqttClient.relayTelemetry(hiveName, payload)
                count = count + 1

            elif count > 20:
                mqttClient.publishGatewayStatus()
                count = 0


class TelemetryMQTT():
    def __init__(self, clientId, brokerUrl):
        self.clientId = clientId
        self.mqttUrl = brokerUrl
        self.client = None
        self.keepalive = 60

    def connect(self):
        self.client = MQTTClient(self.clientId, self.mqttUrl, port=31883, keepalive=self.keepalive)

        try:
            self.client.connect(clean_session=True)
            print("Connected to MQTT broker")
        except:
            print('Unable to connect to MQTT broker')
            reboot()

    def publishGatewayStatus(self, persist=True):
        topic = 'telemetry/gateway/{}'.format(self.clientId)
        payload = str({
            'gateway_name': self.clientId,
            't': getTime(),
            'temperature': readTemperature(),
            'channel': wifiChannel
        }).replace("'", '"').encode()

        self.client.publish(topic, payload, persist)


    def relayTelemetry(self, topic, msg, persist=True):
        topic = 'telemetry/hive/{}'.format(topic)
        msg['t'] = getTime()
        payload = str(msg).replace("'", '"').encode()

        self.client.publish(topic, payload, persist)


def resetAntennas():   # Reset wifi to AP_IF off, STA_IF on and disconnected
    sta = network.WLAN(network.STA_IF)
    ap = network.WLAN(network.AP_IF)
    sta.active(False)
    ap.active(False)
    
    sta.active(True)
    while not sta.active():
        time.sleep(0.1)
        print('sta.active():')
    while sta.isconnected():
        time.sleep(0.1)
        print('sta.isconnected():')


def reboot(delay = REBOOT_DELAY):
    print (f'Rebooting device in {delay} seconds (Ctrl-C to escape).')
    utime.sleep(delay)
    machine.reset()


def parse_json(json_str):
    try:
        # Evaluate the JSON string to convert it into a Python dictionary
        result_dict = eval(json_str)
        if not isinstance(result_dict, dict):
            raise ValueError("JSON does not represent a valid object.")
        return result_dict
    except Exception as e:
        raise ValueError("Invalid JSON format:", str(e))


def syncTime():
    ntptime.settime()


def getTime():
    [ y, M, d, h, m, s, dow, doy] = time.localtime()
    return '{}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z'.format(y, M, d, h, m, s)


def readTemperature():
    fahrenheit = esp32.raw_temperature()
    celcius = (fahrenheit - 32) / 1.8
    return "{0:.2f}".format(celcius)


# def readBatteryLevel():
#     adc = ADC(Pin(13, Pin.IN))
#     voltage = (adc.read() / 4095) * 2 * 3.3 * 1.1
#     # return 22
#     return "{0:.2f}".format(voltage)


def setupAndProxy():
    resetAntennas()
    espNowServer = ESPNowServer()
    espNowServer.setup()
    
    ssid = getStorageVar('ssid')
    password = getStorageVar('pass')
    wifi = Wifi()
    wifi.connect(ssid, password)

    brokerUrl = getStorageVar('mqtt_broker')
    mqttClient = TelemetryMQTT('House', brokerUrl)
    mqttClient.connect()

    syncTime()
    return espNowServer, mqttClient


if __name__ == '__main__':
    modeSwitch = Pin(26, Pin.IN, Pin.PULL_UP)
    mode = modeSwitch.value()
    
    try:
        if mode == 1:
            [espNowServer, mqttClient] = setupAndProxy()
            print('activated and waiting for messages')

            espNowServer.receive(mqttClient)
        else:
            print('serving setup server')
            serveSetupServer()

    except KeyboardInterrupt as err:
        raise err #  use Ctrl-C to exit to micropython repl
    except Exception as err:
        print ('Error during execution:', err)
        # raise err
        reboot()
