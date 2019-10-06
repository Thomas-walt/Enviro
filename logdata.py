#!/usr/bin/env python

# Utilities
import time
import colorsys
import os
import sys
import logging
import mysql.connector
from mysql.connector import Error, errorcode
from subprocess import PIPE, Popen

# Sensors
from enviroplus import gas
# from machine import I2S
try:
    from ltr559 import LTR559
    ltr559 = LTR559()
except ImportError:
   import ltr559
from bme280 import BME280
bme280 = BME280()
Datas = dict()

# Logging
logging.basicConfig(
    format='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

logging.info("""logdata.py - Log recording from Enviro+ sensors""")

# Display
import ST7735
from PIL import Image, ImageDraw, ImageFont
disp = ST7735.ST7735(
    port=0,
    cs=1,
    dc=9,
    backlight=12,
    rotation=270,
    spi_speed_hz=10000000
)
disp.begin()
WIDTH = disp.width
HEIGHT = disp.height

def display_datas():
    global Datas

    img = Image.new('RGB', (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    font_size = 14
    path = os.path.dirname(os.path.realpath(__file__))
    font = ImageFont.truetype(path + "/examples/fonts/Asap/Asap-Bold.ttf", font_size)
    text_colour = (255, 255, 255)
    back_colour = (34, 45, 50)
    draw.rectangle((0, 0, 160, 80), back_colour)

    draw.text((5, 5), time.strftime('%X %x')+' - '+str(Datas['cpu_temp'])+'C', font=font, fill=(0,192,239))
    draw.text((5, 25), 'TEMP : '+str(Datas['temperature'])+'C', font=font, fill=text_colour)
    draw.text((5, 42.5), 'PR : '+str(Datas['pressure'])+'hPa', font=font, fill=text_colour)
    draw.text((5, 57.5), 'HUM : '+str(Datas['humidity'])+'%', font=font, fill=text_colour)

    disp.display(img)

def get_cpu_temperature():
    process = Popen(['vcgencmd', 'measure_temp'], stdout=PIPE, universal_newlines=True)
    output, _error = process.communicate()
    return float(output[output.index('=') + 1:output.rindex("'")])

def readSensors():
    global Datas

    factor = 0.8
    cpu_temp = get_cpu_temperature()
    raw_temp = bme280.get_temperature()
    temperature = raw_temp - ((cpu_temp - raw_temp) / factor)
    datasgas = gas.read_all()

    Datas['cpu_temp'] = round(cpu_temp,2)
    Datas['temperature'] = round(temperature,2)
    Datas['pressure'] = round(bme280.get_pressure(),2)
    Datas['humidity'] = round(bme280.get_humidity(),2)
    Datas['light'] = round(ltr559.get_lux(),2)
    Datas['oxidised'] = round(datasgas.oxidising / 1000,2)
    Datas['reduced'] = round(datasgas.reducing / 1000,2)
    Datas['nh3'] = round(datasgas.nh3 / 1000,2)
    display_datas()

def sendDataToServer():
    readSensors()
    global Datas
    try:
        connection = mysql.connector.connect(
          host="****",
          database="****",
          user="****",
          passwd="****"
        )
        cursor = connection.cursor()
        mySql_insert_query = """INSERT INTO data (temperature, pressure, humidity, light, oxidised, reduced, nh3)
        VALUES (%s, %s, %s, %s, %s, %s, %s) """
        datas = (Datas['temperature'], Datas['pressure'], Datas['humidity'], Datas['light'], Datas['oxidised'], Datas['reduced'], Datas['nh3'])
        cursor.execute(mySql_insert_query, datas)
        connection.commit()
        logging.info("Record inserted successfully into data table")
    except mysql.connector.Error as error:
        logging.info("Failed to insert into data table {}".format(error))
    finally:
        if (connection.is_connected()):
            cursor.close()
            connection.close()
            logging.info("MySQL connection is closed")

try:
    while True:
        sendDataToServer()
        time.sleep(600)
except KeyboardInterrupt:
    logging.info("Log recording stopped")
    disp.set_backlight(0)
    sys.exit(0)
    pass
