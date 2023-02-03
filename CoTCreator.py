#!/usr/bin/env python3

import asyncio
import xml.etree.ElementTree as ET
import uuid
import time

from configparser import ConfigParser

import pytak
import json

with open("cameras.json", "r") as file:
    global data  # declaring data as a global variable
    data = json.load(file)

class MySerializer(pytak.QueueWorker):
    """
    Defines how you process or generate your Cursor-On-Target Events.
    From there it adds the COT Events to a queue for TX to a COT_URL.
    """

    async def handle_data(self, data):
        """
        Handles pre-COT data and serializes to COT Events, then puts on queue.
        """
        event = data
        await self.put_queue(event)

    async def run(self, number_of_iterations=-1):
        """
        Runs the loop for processing or generating pre-COT data.
        """
        for i in data:
            item = tak_sensor(i['name'], i['latitude'], i['longitude'], i['streamURL'], i['path'], i['address'])
            await self.handle_data(item)
            await asyncio.sleep(0.1)


def tak_sensor(cam_name, lat, lon, url, path, address):
    """
    Generates a sensor.
    """
    event_uuid = str(uuid.uuid4())
    video_uuid = str(uuid.uuid4())
    root = ET.Element("event")
    root.set("version", "2.0")
    root.set("type", "b-m-p-s-p-loc")
    root.set("uid", event_uuid)
    root.set("how", "h-g-i-g-o")
    root.set("time", pytak.cot_time())
    root.set("start", pytak.cot_time())
    root.set("stale", pytak.cot_time(3600))
    point = ET.SubElement(root, 'point')
    point.set('lat', str(lat))
    point.set('lon', str(lon))
    point.set('hae', '250')
    point.set('ce', '9999999.0')
    point.set('le', '9999999.0')
    detail = ET.SubElement(root, 'detail')
    status = ET.SubElement(detail, 'status')
    status.set('readiness', 'true')
    ET.SubElement(detail, 'archive')
    video = ET.SubElement(detail, '__video')
    video.set('uid', video_uuid)
    video.set('url', url)
    ConnEntry = ET.SubElement(video, 'ConnectionEntry')
    ConnEntry.set('networkTimeout', '12000')
    ConnEntry.set('uid', video_uuid)
    ConnEntry.set('path', path)
    ConnEntry.set('protocol', 'https')
    ConnEntry.set('bufferTimeout', '-1')
    ConnEntry.set('address', address)
    ConnEntry.set('port', '443')
    ConnEntry.set('roverPort', '-1')
    ConnEntry.set('rtspReliable', '0')
    ConnEntry.set('ignoreEmbeddedKLV', 'false')
    ConnEntry.set('alias', cam_name)
    remarks = ET.SubElement(detail, 'remarks')
    remarks.text = " "
    color = ET.SubElement(detail, 'color')
    color.set('argb', '-1')
    sensor = ET.SubElement(detail, 'sensor')
    sensor.set("vfov", "45")
    sensor.set("elevation", "0")
    sensor.set("fovBlue", "1.0")
    sensor.set("fovRed", "1.0")
    sensor.set("strokeWeight", "0.0")
    sensor.set("roll", "0")
    sensor.set("range", "100")
    sensor.set("azimuth", "270")
    sensor.set("rangeLineStrokeWeight", "0.0")
    sensor.set("fov", "45")
    sensor.set("hideFov", "true")
    sensor.set("rangeLineStrokeColor", "-16777216")
    sensor.set("fovGreen", "1.0")
    sensor.set("displayMagneticReference", "0")
    sensor.set("strokeColor", "-16777216")
    sensor.set("rangeLines", "100")
    sensor.set("fovAlpha", "0.2980392156862745")
    precisionlocation = ET.SubElement(detail, "precisionlocation")
    precisionlocation.set("altsrc", "DTED0")
    link = ET.SubElement(detail, "link")
    link.set("uid", "<YOUR_DEVICE_UUID_HERE>")
    link.set("production_time", pytak.cot_time())
    link.set("type", "a-f-G-U-C")
    link.set("parent_callsign", "<YOUR_CALLSIGN_HERE>")
    link.set("relation", "p-p")
    ET.SubElement(detail, "archive")
    contact = ET.SubElement(detail, "contact")
    contact.set("callsign", cam_name)
    print(f"Added camera: {cam_name}")
    return ET.tostring(root)


async def main():
    """
    The main definition of your program, sets config params and
    adds your serializer to the asyncio task list.
    """
    config = ConfigParser()
    config["mycottool"] = {"COT_URL": "<YOUR_URL_HERE>", "PYTAK_TLS_CLIENT_CERT":"private_key.pem", "PYTAK_TLS_CLIENT_KEY":"private_key.pem", "PYTAK_TLS_DONT_VERIFY": "true"}
    config = config["mycottool"]

    # Initializes worker queues and tasks.
    clitool = pytak.CLITool(config)
    await clitool.setup()

    # Add your serializer to the asyncio task list.
    clitool.add_tasks(set([MySerializer(clitool.tx_queue, config)]))
    print("Starting in 15 seconds...")
    await asyncio.sleep(15)
    # Start all tasks.
    await clitool.run()


if __name__ == "__main__":
    asyncio.run(main())