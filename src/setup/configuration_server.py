import network, machine, utime, gc
from ubinascii import hexlify
from esp32 import NVS

try:
    import usocket as socket
except:
    import socket

gc.collect()
nvs = NVS('conf')

AP_SSID = 'MicroPython-AP'
AP_PASSWOD = '123456789'
REBOOT_DELAY = 2

settings = [
    'ssid',
    'pass',
    'name',
    'mqtt_broker',
    'mqtt_topic',
    'dht11_pin',
    'ds28b20_pin',
    'mac',
    'peer',
    'freq'
]

routes = []
routeTree = {}
contentTypes = {
    'html': 'text/html',
    'css': 'text/css'
}


def saveDeviceInfo():
    setStorage({
        'mac': hexlify(network.WLAN().config('mac'),':').decode(),
        'freq': str(machine.freq() / 1000000) # megahertz
    })


def setupAP():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=AP_SSID, password=AP_PASSWOD, security=3)

    while ap.active() == False:
        pass

    print('Connection successful')
    print(ap.ifconfig())


def setupServer():
    # bind socket server to port 80
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 80))
    s.listen(5)
    return s


def reboot(delay = REBOOT_DELAY):
    print (f'Rebooting device in {delay} seconds (Ctrl-C to escape).')
    utime.sleep(delay)
    machine.reset()


def identify():
    led = machine.Pin(13, machine.Pin.OUT)
    count = 6
    while count > 0:
        count = count - 1
        led.value(1)
        utime.sleep_ms(400)
        led.value(0)
        utime.sleep_ms(250)


def setStorage(data):
    for key, value in data.items():
        nvs.set_blob(key, value.encode())


def getStorageVar(key):
    value = bytearray(96)
    try:
        length = nvs.get_blob(key, value)
        value = value.decode('utf-8')[:length]
    except OSError as e:
        if 'ESP_ERR_NVS_NOT_FOUND' in str(e):
            print('Missing NVS key "{}", adding blank value'.format(key))
            value = ''
            setStorage({key: value})
        else:
            raise e

    return value


def importHTML(filename, route, hydration=None):
    global routeTree
    f = open(filename)
    html = f.read()
    html = ' '.join(html.split())
    f.close()

    if hydration:
        html = hydrateHTMLTemplate(html, hydration)

    routeTree[route] = html


def hydrateHTMLTemplate(source, keys):
    for key in keys:
        templateString = '{{ ' + key + ' }}'
        source = source.replace(templateString, getStorageVar(key))
    return source


def importRoutes():
    global routes
    importHTML('index.html', '/', settings),
    importHTML('success.html', '/save')
    importHTML('styles.css', '/styles.css')
    routes = routeTree.keys()


def htmlEncodedStrings(string):
    if '%3A' in string:
        string = string.replace('%3A', ':')
    return string


def parsePostRequest(req):
    reqString = str(req).split()[-1]
    reqString = reqString.split('\\n')[-1]
    reqString = reqString[:-1]
    args = reqString.split('&')

    data = {}
    for arg in args:
        [key, value] = arg.split('=')
        data[key] = htmlEncodedStrings(value)

    print('got post data: ' + str(data))
    return data


def getContentType(path):
    try:
        extension = path.split('.')[1]
        return contentTypes[extension]
    except:
        return contentTypes['html']


def response200(conn, text, contentType='text/html'):
    conn.send('HTTP/1.1 200 OK\n')
    conn.send('Content-Type: %s\n' % contentType)
    conn.send('Connection: close\n\n')
    conn.send(text)
    conn.close()


def response404(conn):
    conn.send('HTTP/1.1 404 NOT FOUND\n')
    conn.send('Connection: close\n\n')
    conn.close()


def response400(conn):
    conn.send('HTTP/1.1 400 BAD REQUEST\n')
    conn.send('Connection: close\n\n')
    conn.close()


def handleRequest(conn):
    request = conn.recv(1024)

    requestSegments = request.split()
    if len(requestSegments) <= 2:
        response400(conn)

    method = requestSegments[0].decode('utf-8')
    path = requestSegments[1].decode('utf-8')
    contentType = getContentType(path)

    if path in routes and method == 'GET':
        response200(conn, routeTree[path], contentType)

    elif path == '/save' and method == 'POST':
        setStorage(parsePostRequest(request))
        importHTML('index.html', '/', settings),
        response200(conn, routeTree[path], contentType)

    elif path == '/reboot' and method == 'POST':
        response200(conn, 'ok', contentType)
        reboot()

    elif path == '/identify' and method == 'POST':
        response200(conn, 'ok', contentType)
        identify()

    else:
        response404(conn)


def serverRequests(s):
    while True:
        conn, addr = s.accept()
        print('Received req from: ' + str(addr))
        handleRequest(conn)


def serveSetupServer():
    setupAP()
    saveDeviceInfo()
    s = setupServer()
    importRoutes()

    serverRequests(s)


if __name__ == '__main__':
    try:
        serveSetupServer()
    except KeyboardInterrupt as err:
        raise err #  use Ctrl-C to exit to micropython repl
    except Exception as err:
        print ('Error during execution:', err)
        reboot()