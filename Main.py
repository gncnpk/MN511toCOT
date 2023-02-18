#!/usr/bin/env python3

import asyncio
import xml.etree.ElementTree as ET
import uuid
import time
import requests

from configparser import ConfigParser

import pytak
import json

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
        while True:
            # Initalize variables with queries
            road_reports_body = [ { "query": "query MapFeatures($input: MapFeaturesArgs!, $plowType: String) { mapFeaturesQuery(input: $input) { mapFeatures { bbox tooltip uri features { id geometry properties } __typename ... on Camera { views(limit: 5) { uri ... on CameraView { url } category } } ... on Plow { views(limit: 5, plowType: $plowType) { uri ... on PlowCameraView { url } category } } } error { message type } } }", "variables": { "input": { "north": 45.27842, "south": 44.64048, "east": -92.72554, "west": -93.37511, "zoom": 11, "layerSlugs": [ "roadReports" ] }, "plowType": "plowCameras" } } ]
            cameras_body = [ { "query": "query MapFeatures($input: MapFeaturesArgs!, $plowType: String) { mapFeaturesQuery(input: $input) { mapFeatures { bbox tooltip uri features { id geometry properties } __typename ... on Camera { views(limit: 5) { uri ... on CameraView { url } category } } ... on Plow { views(limit: 5, plowType: $plowType) { uri ... on PlowCameraView { url } category } } } error { message type } } }", "variables": { "input": { "north": 45.32945, "south": 44.69207, "east": -92.45245, "west": -93.85596, "zoom": 11, "layerSlugs": [ "normalCameras" ], "nonClusterableUris": [ "dashboard" ] }, "plowType": "plowCameras" } } ]
            # Initialize list variables containing cameras + road report data
            roadReports = []
            camerasWithStreaming = []

            apiEndpointURL = "https://511mn.org/api/graphql"
            poll_interval: int = int(self.config.get('POLL_INTERVAL'))
            # Processing takes some time before sending out CoT events, this ensures markers don't disappear before processing has finished
            processing_latency = 600
            # Perform GET requests to get the latest road report + camera data
            road_reports_request = requests.post(apiEndpointURL, json=road_reports_body) 
            cameras_request = requests.post(apiEndpointURL, json=cameras_body) 
            road_reports_json_data = road_reports_request.json()
            cameras_json_data = cameras_request.json()
            # Process road reports into a simple dict
            for i in road_reports_json_data[0]['data']['mapFeaturesQuery']['mapFeatures']:
                try:
                    description = i['tooltip'].split(':')[1][1:]
                    dataToAppend = {
                        "description": description,
                        "latitude": i['features'][0]['geometry']['coordinates'][1],
                        "longitude": i['features'][0]['geometry']['coordinates'][0],
                        "uuid": i['uri'].split('/')[1]
                    }
                    roadReports.append(dataToAppend)
                except:
                    continue
            # Process camera data into a simple dict and test for streaming capabilities
            for i in cameras_json_data[0]['data']['mapFeaturesQuery']['mapFeatures']:
                try:
                    camName = i['tooltip']
                    camId = i['views'][0]['url'].split('/MN/')[1].split('?')[0]
                    streamURL = f"https://video.dot.state.mn.us/public/{camId}.stream/playlist.m3u8"
                    address = streamURL.split('https://')[1].split('/')[0]
                    path = streamURL.split('https://video.dot.state.mn.us')[1]
                    r2 = requests.head(streamURL)
                    if r2.status_code == 200:
                        i['views'][0]['streamURL'] = streamURL
                        dataToAppend = {
                            "name": camName,
                            "streamURL": streamURL,
                            "latitude": i['features'][0]['geometry']['coordinates'][1],
                            "longitude": i['features'][0]['geometry']['coordinates'][0],
                            "path": path,
                            "address": address
                        }
                        camerasWithStreaming.append(dataToAppend)
                except:
                    continue
            # Create CoT events from road reports dict
            for i in roadReports:
                item = tak_roadReport(i['latitude'], i['longitude'], i['uuid'], i['description'], poll_interval + processing_latency)
                await self.handle_data(item)
                await asyncio.sleep(0.1)
            for i in camerasWithStreaming:
                item = tak_sensor(i['name'], i['latitude'], i['longitude'], i['streamURL'], i['path'], i['address'], poll_interval + processing_latency)
                await self.handle_data(item)
                await asyncio.sleep(0.1)

            print(f"Added {len(roadReports)} road reports and {len(camerasWithStreaming)} cameras! Checking in {poll_interval // 60} minutes...")
            await asyncio.sleep(poll_interval)


def tak_sensor(cam_name, lat, lon, url, path, address, poll_interval):
    """
    Generates a sensor.
    """
    event_uuid = f"MN511-{cam_name}-CAMERA"
    video_uuid = f"MN511-{cam_name}-VIDEO"
    root = ET.Element("event")
    root.set("version", "2.0")
    root.set("type", "b-m-p-s-p-loc")
    root.set("uid", event_uuid)
    root.set("how", "h-g-i-g-o")
    root.set("time", pytak.cot_time())
    root.set("start", pytak.cot_time())
    root.set("stale", pytak.cot_time(poll_interval))
    point = ET.SubElement(root, 'point')
    point.set('lat', str(lat))
    point.set('lon', str(lon))
    point.set('hae', '250')
    point.set('ce', '9999999.0')
    point.set('le', '9999999.0')
    detail = ET.SubElement(root, 'detail')
    status = ET.SubElement(detail, 'status')
    status.set('readiness', 'true')
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
    contact = ET.SubElement(detail, "contact")
    contact.set("callsign", cam_name)
    return ET.tostring(root)

def tak_roadReport(lat, lon, uuid, description, poll_interval):
    event_uuid = uuid
    root = ET.Element("event")
    root.set("version", "2.0")
    root.set("type", "a-u-G")
    root.set("uid", event_uuid)
    root.set("how", "h-g-i-g-o")
    root.set("time", pytak.cot_time())
    root.set("start", pytak.cot_time())
    root.set("stale", pytak.cot_time(poll_interval))
    point = ET.SubElement(root, 'point')
    point.set('lat', str(lat))
    point.set('lon', str(lon))
    point.set('hae', '250')
    point.set('ce', '9999999.0')
    point.set('le', '9999999.0')
    detail = ET.SubElement(root, 'detail')
    status = ET.SubElement(detail, 'status')
    status.set('readiness', 'true')
    precisionlocation = ET.SubElement(detail, "precisionlocation")
    precisionlocation.set("altsrc", "DTED0")
    remarks = ET.SubElement(detail, 'remarks')
    remarks.text = description
    contact = ET.SubElement(detail, "contact")
    contact.set("callsign", "Road Report")
    color = ET.SubElement(detail, 'color')
    color.set('argb', '-1')
    usericon = ET.SubElement(detail, 'usericon')
    usericon.set('iconsetpath','f7f71666-8b28-4b57-9fbb-e38e61d33b79/Google/caution.png')
    return ET.tostring(root)

async def main():
    """
    The main definition of your program, sets config params and
    adds your serializer to the asyncio task list.
    """
    config = ConfigParser()
    config.read('config.ini')
    config = config["mn511tocot"]

    # Initializes worker queues and tasks.
    clitool = pytak.CLITool(config)
    await clitool.setup()

    # Add your serializer to the asyncio task list.
    clitool.add_tasks(set([MySerializer(clitool.tx_queue, config)]))
    # Start all tasks.
    await clitool.run()


if __name__ == "__main__":
    asyncio.run(main())