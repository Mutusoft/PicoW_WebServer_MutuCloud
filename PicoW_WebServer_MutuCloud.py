# This code based on original code from Raspberry Pi
# Connecting to the internet with pico w doc
# Modified for usage with Mutusoft's wattMetr http://mutusoft.com/kitpages/
# Code provided without any warranty and is free to use

#verze 20250110

import network
import socket
import time
import json
import urequests
from machine import Pin, UART
import uasyncio as asyncio
import struct

# Wifi a LAN parametry
ssid = "nastavte"
password = "nastavte"

# pokud je dhcp = 1, pak parametry ip, mask, gw ani dns neni potreba vyplnovat
# pro zadani pevne IP adresy a parametru LAN site, zadejte dhcp = 0
dhcp = 1
ip = 'Pevná_IP_addr'
mask = 'IP_Maska'
gw = 'Default_Gateway'
dns = 'DNS_server'
# Wifi a LAN parametry

# MutuCloud parametry
# příklad dev_id = '8389CE2A1A9A48FBA1859696EF1CB2CB6C157CA8'
dev_id = '8389CE2A1A9A48FBA1859696EF1CB2CB6C157CA8'
# použijte dle svého uvážení, příklad dev_name = 'wattMetr v ložnici'
dev_name = 'wattMetr TEST'
# mutucloud_url neměnte!
mutucloud_url = 'http://mutusoft.com/kitpages/wmhp.aspx'
# MutuCloud parametry


# Obnova hodnot historie
# pokud je Write_History=1, pak se po startu PicoW zapisi do wattMetru nasledujici hodnoty (mozne vyuzit po upgrade FW, kdy dochazi ke ztrate historie)
# po zapisu dat do wattmetru, je dobre nastavit Write_History=0
Write_History=1
# zadani ID - int(x) - za x zadejte libovolne cislo mezi 1-255, pro zapis historickych hodnot je potreba, aby bylo ID jine nez pri predchozim zapisu historickych dat
# vzdy, kdyz dojde ke zmene ID a Write_History=1, wattmetr zapise nize uvedena data do Flash 
History_ID = int(155)
# nasledujici hodnoty zadavejte jako cisla s desetinnou carkou (float)
# v hodinach
History_Motohodiny = 99999.9
# ve WattHodinach
History_EnergieCelkem = 55555555.9
# v MegaWattHodinach
History_Mesice = [  11.99, 10.99, 9.99, 8.99, 7.99, 6.99, 5.99, 4.99, 3.99, 2.99, 1.99, 5.99 ]
# v MegaWattHodinach
History_Roky10 = [  9.99, 8.99, 7.99, 6.99, 5.99, 4.99, 3.99, 2.99, 1.99, 5.99 ]

onboard = Pin("LED", Pin.OUT, value=0)

html1 = """<!DOCTYPE html>
<html>
    <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>wattMetr web by Mutusoft.com</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-EVSTQN3/azprG1Anm3QDgpJLIm9Nao0Yz1ztcQTwFspd3yD65VohhpuuCOmLASjC" crossorigin="anonymous">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
    </head>
    <body>
    <div class="container text-center">
        <div class="row">
            <div class="col-sm-3"></div>
            <div class="col-sm-6">
                <a href="http://mutusoft.com/kitpages"><img src="http://mutusoft.com/Grafika/mutusoft_picture.png" width="150" /></a>
                <h2>{DeviceName}</h2>
            </div>
            <div class="col-sm-3"></div>
        </div>
        
        <div class="row">
            <div class="col-sm-3"></div>
            <div class="col-sm-6">
                    <table class="table">"""
                    
html2 = """
                        <tbody>
                          <tr>
                            <td style="text-align: left">Datum a Čas:</td>
                            <td style="text-align: right"><strong>{TimeStamp}</strong></td>
                          </tr>
                          <tr>
                            <td style="text-align: left">Uptime:</td>
                            <td style="text-align: right"><strong>{Uptime}</strong></td>
                          </tr>  
                          <tr>
                            <td style="text-align: left">Energie za den:</td>
                            <td style="text-align: right"><strong>{EnergyDay:10.3f} kWh</strong></td>
                          </tr>
                          <tr>
                            <td style="text-align: left">Energie celkem:</td>
                            <td style="text-align: right"><strong>{Energy:10.0f} kWh</strong></td>
                          </tr>
                            <tr>
                                <td style="text-align: left">Motohodiny:</td>
                                <td style="text-align: right"><strong>{MotoH:10.1f} h</strong></td>
                            </tr>                          
                              
                            <tr>
                                <td style="text-align: left">Firmware:</td>
                                <td style="text-align: right"><strong>{Firmware}</strong></td>
                            </tr>                          
                          </tbody>
"""                          
                          
html3 = """
                </table>
            </div>
            <div class="col-sm-3"></div>
        </div>
        
        <div class="row">
            <div class="col-sm-3"></div>
            <div class="col-sm-6">
                    <table class="table">
                        <tbody>
                          <tr>
                          <td></td>
                            <td><div id="Ampermetr" style="width: 150px; height: 150px; margin: Auto;"></div></td>
                            <td><div id="Voltmetr" style="width: 150px; height: 150px; margin: Auto;"></div></td>
                            <td></td>
                          </tr>
                          <tr>
                          <td></td>
                            <td><div id="Wattmetr" style="width: 150px; height: 150px; margin: Auto;"></div></td>
                            <td><div id="Tempmetr" style="width: 150px; height: 150px; margin: Auto;"></div></td>
                            <td></td>
                           </tr>
                        </tbody> 
                </table>
            </div>
            <div class="col-sm-3"></div>
        </div>
        
        <div class="row">
            <div class="col-sm-3"></div>
            <div class="col-sm-6">
                <canvas id="tempChart" style="width:100%;max-width:700px"></canvas>
            </div>
            <div class="col-sm-3"></div>
        </div>
        <div class="row">
            <div class="col-sm-3"></div>
            <div class="col-sm-6">
                <canvas id="pwrChart" style="width:100%;max-width:700px"></canvas>
            </div>
            <div class="col-sm-3"></div>
        </div>
        <div class="row">
          <div class="col-sm-3"></div>
          <div class="col-sm-6">
              <canvas id="UIChart" style="width:100%;max-width:700px"></canvas>
          </div>
        <div class="col-sm-3"></div>
        </div>
        <div class="row">
            <div class="col-sm-3"></div>
            <div class="col-sm-6">
                <canvas id="enDeChart" style="width:100%;max-width:700px"></canvas>
            </div>
            <div class="col-sm-3"></div>
        </div>
        <div class="row">
            <div class="col-sm-3"></div>
            <div class="col-sm-6">
                <canvas id="enMeChart" style="width:100%;max-width:700px"></canvas>
            </div>
            <div class="col-sm-3"></div>
        </div>
        <div class="row">
            <div class="col-sm-3"></div>
            <div class="col-sm-6">
                <canvas id="enRoChart" style="width:100%;max-width:700px"></canvas>
            </div>
            <div class="col-sm-3"></div>
        </div>
        <div class="row">
            <div class="col-sm-3"></div>
            <div class="col-sm-6">
                <canvas id="en10RChart" style="width:100%;max-width:700px"></canvas>
            </div>
            <div class="col-sm-3"></div>
        </div>
    </div>
    
    <script>
"""

html4 = """
const xTempValues = [{xTempValues}];
const yTempValues = [{yTempValues}];
const xPwrValues = [{xPwrValues}];
const yPwrValues = [{yPwrValues}];
const xEnDenValues = [{xEnDenValues}];
const yEnDenValues = [{yEnDenValues}];
const xEnMesValues = [{xEnMesValues}];
const yEnMesValues = [{yEnMesValues}];
const xEnRokValues = [{xEnRokValues}];
const yEnRokValues = [{yEnRokValues}];
const xEn10RValues = [{xEn10RValues}];
const yEn10RValues = [{yEn10RValues}];
const AMPS = {Current:10.1f};
const VOLTS = {Voltage:10.0f}; 
const WATTS = {Power:10.0f};
const CELSIUS = {Teplota:10.1f};
const xUValues = [{xUValues}];
const yUValues = [{yUValues}];
const xIValues = [{xIValues}];
const yIValues = [{yIValues}];
"""

html5 = """ 
    new Chart("tempChart", {
      type: "line",
      data: {
        labels: xTempValues,
        datasets: [{
          label: 'Teplota [°C]',
          fill: false,
          lineTension: 0,
          pointRadius: 2,
          borderWidth: 2,          
          backgroundColor: "Orange",
          borderColor: "DarkOrange",
          data: yTempValues
        }]
      },
      options: {
                 scales: {
                    x: {
                        ticks: {
                          callback: function(val, index) {
                            if (this.getLabelForValue(val) == 0) return 'Nyní';
                            if (this.getLabelForValue(val) == 32) return 'před 3h';
                            if (this.getLabelForValue(val) == 64) return 'před 6h';
                            if (this.getLabelForValue(val) == 96) return 'před 9h';
                            if (this.getLabelForValue(val) == 127) return 'před 12h';
                          }
                        }
          }
        }
      }
    });

    new Chart("pwrChart", {
      type: "line",
      data: {
        labels: xPwrValues,
        datasets: [{
          label: 'Výkon [kW]',
          fill: true,
          lineTension: 0.0,
          pointRadius: 2,
          borderWidth: 2,
          backgroundColor: "LightSalmon",
          borderColor: "OrangeRed",
          data: yPwrValues
        }]
      },
      options: {
        legend: {display: false},
        scales: {
                    x: {
                        ticks: {
                          callback: function(val, index) {
                            if (this.getLabelForValue(val) == 0) return 'Nyní';
                            if (this.getLabelForValue(val) == 32) return 'před 3h';
                            if (this.getLabelForValue(val) == 64) return 'před 6h';
                            if (this.getLabelForValue(val) == 96) return 'před 9h';
                            if (this.getLabelForValue(val) == 127) return 'před 12h';
                          }
                        },
          }
        }
      }
    });
    
    new Chart("UIChart", {
    type: "line",
    data: {
        labels: xUValues,
        datasets: [{
            yAxisID: 'y1',
            label: 'Napětí [V]',
            fill: false,
            lineTension: 0.0,
            pointRadius: 2,
            borderWidth: 2,
            backgroundColor: "LightBlue",
            borderColor: "DarkSlateBlue",
            data: yUValues
            },
            {
            yAxisID: 'y2',
            label: 'Proud [A]',
            fill: false,
            lineTension: 0.0,
            pointRadius: 2,
            borderWidth: 2,
            backgroundColor: "Tomato",
            borderColor: "Crimson",
            data: yIValues
            },
        ]
    },
    options: {
        legend: { display: false },
        scales: {
            x: {
                ticks: {
                    callback: function (val, index) {
                        if (this.getLabelForValue(val) == 0) return 'Nyní';
                        if (this.getLabelForValue(val) == 32) return 'před 3h';
                        if (this.getLabelForValue(val) == 64) return 'před 6h';
                        if (this.getLabelForValue(val) == 96) return 'před 9h';
                        if (this.getLabelForValue(val) == 127) return 'před 12h';
                    }
                },
            },
            y1: {
                type: 'linear',
                display: true,
                position: 'left',
                grid: { display: false },
            },
            y2: {
                type: 'linear',
                display: true,
                position: 'right',
                grid: { display: false },
            }

        }
        }
    });

    new Chart("enDeChart", {
      type: "bar",
      data: {
        labels: xEnDenValues,
        datasets: [{
          label: 'Výroba za 1 den [kWh]',
          backgroundColor: "LawnGreen",
           data: yEnDenValues
        }]
      },
      options: {
        legend: {display: false}
      }
    });

    new Chart("enMeChart", {
      type: "bar",
      data: {
        labels: xEnMesValues,
        datasets: [{
          label: 'Výroba za 1 Měsíc [kWh]',
          backgroundColor: "LimeGreen",
          data: yEnMesValues
        }]
      },
      options: {
        legend: {display: false},
      }
    });

    new Chart("enRoChart", {
      type: "bar",
      data: {
        labels: xEnRokValues,
        datasets: [{
          label: 'Výroba za 1 Rok [MWh]',
          backgroundColor: "Green",
          data: yEnRokValues
        }]
      },
      options: {
        legend: {display: false},
      }
    });

    new Chart("en10RChart", {
      type: "bar",
      data: {
        labels: xEn10RValues,
        datasets: [{
          label: 'Výroba za 10 let [MWh]',
          backgroundColor: "DarkGreen",
          data: yEn10RValues
        }]
      },
      options: {
        legend: {display: false},
      }
    });

      google.charts.load('current', {'packages':['gauge']});
      google.charts.setOnLoadCallback(drawAmpMetr);
      google.charts.setOnLoadCallback(drawVoltMetr);
      google.charts.setOnLoadCallback(drawWattMetr);
      google.charts.setOnLoadCallback(drawTempMetr);
      
      function drawAmpMetr() {

        var data = google.visualization.arrayToDataTable([
          ['Label', 'Value'],
          ['A', AMPS],
        ]);

        var options = {
          width: 150, height: 150,
          greenFrom: 5, greenTo: 15,
          redFrom: 18, redTo: 20,
          yellowFrom:15, yellowTo: 18,
          minorTicks: 5,
          min: 0,
          max: 20
        };

        var AmpMetr = new google.visualization.Gauge(document.getElementById('Ampermetr'));

        AmpMetr.draw(data, options);
      }    
      
      function drawVoltMetr() {

        var data = google.visualization.arrayToDataTable([
          ['Label', 'Value'],
          ['V', VOLTS],
        ]);

        var options = {
          width: 150, height: 150,
          greenFrom: 190, greenTo: 250,
          yellowFrom:250, yellowTo: 300,
          redFrom: 300, redTo: 330,
          minorTicks: 5,
          min: 0,
          max: 330
        };

        var VoltMetr = new google.visualization.Gauge(document.getElementById('Voltmetr'));

        VoltMetr.draw(data, options);
      }
      
      
       function drawWattMetr() {

        var Wattmetr_data = google.visualization.arrayToDataTable([
          ['Label', 'Value'],
          ['W', WATTS],
        ]);

        var options = {
          width: 150, height: 150,
          greenFrom: 1500, greenTo: 2400,
          redFrom: 2800, redTo: 3000,
          yellowFrom: 2400, yellowTo: 2800,
          minorTicks: 5,
          min: 0,
          max: 3000
        };

        var Wattmetr = new google.visualization.Gauge(document.getElementById('Wattmetr'));

        Wattmetr.draw(Wattmetr_data, options);
      }
      
      
       function drawTempMetr() {

        var Tempmetr_data = google.visualization.arrayToDataTable([
          ['Label', 'Value'],
          ['°C', CELSIUS],
        ]);

        var options = {
          width: 150, height: 150,
          greenFrom: 35, greenTo: 65,
          yellowFrom: 65, yellowTo: 85,
          redFrom: 85, redTo: 90,
          minorTicks: 5,
          min: 0,
          max: 90
        };

        var Tempmetr = new google.visualization.Gauge(document.getElementById('Tempmetr'));

        Tempmetr.draw(Tempmetr_data, options);
      }

    setTimeout(function () {
        window.location.reload();
    }, 60000);
    
</script>

</body>

</html>


































"""

wlan = network.WLAN(network.STA_IF)
uart0 = UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1), rxbuf=4096, timeout_char = 100)
rxData = bytes()
rxDataStr = "<undefined>"
json_decoded = json.loads('{}')
err_in_json = 0


def connect_to_network():
    global ssid, password, wlan, dhcp
    wlan.active(True)
    wlan.config(pm = 0xa11140) # Disable power-save mode
    
    print(ssid, password, wlan)
    wlan.connect(ssid, password)
    max_wait = 20
    while max_wait > 0:
        if wlan.status() >= 2:
            break
        max_wait -= 1
        print('Připojuji se k Wifi ...', wlan.status())
        time.sleep(1)
        #wdt.feed()
        onboard.on()
        time.sleep_ms(200)
        onboard.off()
        
    print('wlan status = ', wlan.status())
    if (wlan.status() == -1):
        print('Wifi je spojení přerušeno.')
    elif (wlan.status() == -2):
        print('Wifi nenalezena.')
    elif (wlan.status() == -3):
         print('Wifi nesprávné heslo.')
    elif (wlan.status() == 1):
         print('Wifi pokus o připojení nedokončen.')
    elif (wlan.status() == 0):
         print('Wifi žádná v dosahu')
    elif (wlan.status() == 2 | wlan.status() == 3):
        print('Wifi připojena')
        if(dhcp == 0):
            wlan.ifconfig((ip, mask, gw, dns))
        status = wlan.ifconfig()
        print('status = ', status)
    else:
        print('Wifi neznámý status: ', wlan.status())

def create_web():
    global rxDataStr, json_decoded
    global html1,html2,html3,html4,html5
    #json_decoded = json.loads(rxDataStr)
    #print(rxDataStr)
    if (len(json_decoded) == 0):
        return [ '<h2>No Data Received</h2>', '', '', '', '' ]
    i = 0
    ytemp_data = ''
    xtemp_data = ''
    for temp in json_decoded['Temp12h[C]']:
        #temp_data = temp_data + '{x:' + str(i) + ',y:' + str(temp) + '},\n'
        ytemp_data = ytemp_data + str(temp) + ','
        xtemp_data = xtemp_data + str(i) + ','
        i += 1

    #vykon
    i = 0
    xpwr_data = ''
    ypwr_data = ''
    for pwr in json_decoded['Power12h[kW]']:
        ypwr_data = ypwr_data + str(pwr) + ','
        xpwr_data = xpwr_data + str(i) + ','
        i += 1
   
    #energie den
    i = 0
    xenden_data = ''
    yenden_data = ''
    for en in json_decoded['EnergyDay[kWh]']:
        yenden_data = yenden_data + str(en) + ','
        xenden_data = xenden_data + str(i) + ','
        i += 1
   
    #energie mesic
    i = 0
    xenmes_data = ''
    yenmes_data = ''
    for en in json_decoded['EnergyMonth[kWh]']:
        yenmes_data = yenmes_data + str(en) + ','
        i += 1
        xenmes_data = xenmes_data + str(i) + ','
        
    #energie rok
    i = 0
    xenrok_data = ''
    yenrok_data = ''
    for en in json_decoded['EnergyYear[MWh]']:
        yenrok_data = yenrok_data + str(en) + ','
        i += 1
        xenrok_data = xenrok_data + str(i) + ','

        
    #energie 10 let
    i = 0
    xen10r_data = ''
    yen10r_data = ''
    for en in json_decoded['Energy10Y[MWh]']:
        yen10r_data = yen10r_data + str(en) + ','
        i += 1
        xen10r_data = xen10r_data + str(i) + ','
         
    #napeti
    i = 0
    xU_data = ''
    yU_data = ''
    for volt in json_decoded['Voltage12h[V]']:
        yU_data = yU_data + str(volt) + ','
        i += 1
        xU_data = xU_data + str(i) + ','         
         
    #proud
    i = 0
    xI_data = ''
    yI_data = ''
    for amp in json_decoded['Current12h[A]']:
        yI_data = yI_data + str(amp) + ','
        i += 1
        xI_data = xI_data + str(i) + ','  

    # uptime
    time = json_decoded['Uptime[s]']

    day = time // (24 * 3600)
    time = time % (24 * 3600)
    hour = time // 3600
    time %= 3600
    minutes = time // 60
    time %= 60
    seconds = time
    uptime = ( "%dd, %dh, %dmin, %ds" % (day, hour, minutes, seconds))
    #html0 = 'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n'
    #html1
    aux0 = html1.format(DeviceName = dev_name)
    aux1 = html2.format(TimeStamp = json_decoded['TimeStamp'], EnergyDay = json_decoded['EnergyDayAcc[kWh]'], Energy = json_decoded['EnergyAllAcc[kWh]'], Uptime = uptime, MotoH = json_decoded['MotoH[h]'], Firmware = json_decoded['Firmware'])
    #html3
    aux2 = html4.format(xTempValues = xtemp_data, yTempValues = ytemp_data, xPwrValues = xpwr_data, yPwrValues = ypwr_data, xUValues = xU_data, yUValues = yU_data, xIValues = xI_data, yIValues = yI_data, xEnDenValues = xenden_data, yEnDenValues = yenden_data, xEnMesValues = xenmes_data, yEnMesValues = yenmes_data, xEnRokValues = xenrok_data, yEnRokValues = yenrok_data, xEn10RValues = xen10r_data, yEn10RValues = yen10r_data, Voltage = json_decoded['Voltage[V]'], Current = json_decoded['Current[A]'], Power = json_decoded['Power[W]'], Teplota = json_decoded['Temperature[C]'] )
    
    #print(json_decoded)
    
    #return [ html0, html1, html2, html3, html4, html5 ]
    return [ aux0, aux1, html3, aux2, html5 ]

def push_web():
    global err_in_json, mutucloud_url, dev_id, rxDataStr
    
    #pokud se maji ukladat i hruba json data, pak send_json=1 jinak send_json=0
    send_json = 0
    
    if (err_in_json == 1 ):
        print("pushing web Skipped ...")
        return
    else:
        print("pushing web")
    
    data = ''
    json_param = ''
    
    if (send_json):
        json_param = '&json=1'

    headers  = {'Content-Type': 'MutuCloudDevId=' + dev_id}
    headers_json = {'Content-Type': 'MutuCloudDevId=' + dev_id + json_param}
   
    for html in create_web():
        data = data + html

    try:
        print(mutucloud_url, headers)
        response = urequests.post(mutucloud_url, data=data, headers=headers)
        if (send_json): 
            response = urequests.post(mutucloud_url, data=rxDataStr, headers=headers_json)
        print(response)
    except  Exception as e:
         print("Web push error ...", e)
    
async def serve_client(reader, writer):
    print("Client connected")
    request_line = await reader.readline()
    print("Request:", request_line)
    while await reader.readline() != b"\r\n":
        pass
    request = str(request_line)
    writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    for html in create_web():
        writer.write(html)
    await writer.drain()
    await writer.wait_closed()
    print("Client disconnected")


def uart0_rxh():
    global rxDataStr, json_decoded, err_in_json
    
    while uart0.any() > 0:
        print('Rx chars = ',uart0.any())
        rxData = uart0.read()
    
    err_in_json = 0
    try:
        rxDataStr = rxData.decode('utf-8')
        #json_decoded = json.loads(rxDataStr)
        decoded_tmp = json.loads(rxDataStr)
        print('JSON OK')
    except:
        print('JSON not parsed')
        err_in_json = 1
      
    print(rxData)
    
    if (err_in_json == 0):
        json_decoded = decoded_tmp
    #else:
        #json_decoded = json.loads('{}')
        
def uart0_write_history():
    # ba = bytearray(struct.pack("f", value))
    # interval mezi jednotlivymi uart0.write(ba) je cca 1.8ms
    # motohodiny
    uart0.write('START\0')
    ba = bytearray(struct.pack("f", History_Motohodiny))
    print('History_Motohodiny:', [ "0x%02x" % b for b in ba ])
    uart0.write(ba)
    # energie celkem
    ba = bytearray(struct.pack("f", History_EnergieCelkem))
    print('History_EnergieCelkem:', [ "0x%02x" % b for b in ba ])
    uart0.write(ba)
    # mesicni historie
    for mesic in range(12):
        ba = bytearray(struct.pack("f", History_Mesice[mesic]))
        print('Mesic ', mesic, ': ', [ "0x%02x" % b for b in ba ])
        uart0.write(ba)
    # desetileta historie
    for rok in range(10):
        ba = bytearray(struct.pack("f", History_Roky10[rok]))
        print('Rok ', rok, ': ', [ "0x%02x" % b for b in ba ])
        uart0.write(ba)
    # history ID
    ba = bytearray(struct.pack("i", History_ID))
    uart0.write(ba) 
    # konec
    uart0.write('FINISH\0')
    
        
async def main():
    #global wdt
    onboard.on()
    print('Startuju main()')
    time.sleep(1)
    onboard.off()
    connect_to_network()
    onboard.off()
    time.sleep(1)
    print('Startuju webserver...')
    asyncio.create_task(asyncio.start_server(serve_client, "0.0.0.0", 80))
    push_timer = 0
    while True:
        if (Write_History):
            uart0_write_history()
            
        if (uart0.any()):
            uart0_rxh()

        status = wlan.ifconfig()
        if (wlan.isconnected()):
            if (status[0] != ''):
                print('Připojeno IP -- ', status[0])
                onboard.on()
            else:
                print('Připojeno bez IP')
                onboard.off()
        else:
            onboard.off()
            connect_to_network()
        if (push_timer >= 60):
            push_timer = 0
            push_web()
        push_timer = push_timer + 1
        #wdt.feed()        
        await asyncio.sleep(1)


try:
    asyncio.run(main())
except Exception as e:
    print("Run Error: ", e)
finally:
    print ("Program ukončen ... restart")
    time.sleep(5)
    machine.reset()
