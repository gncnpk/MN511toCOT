import requests
import json
import time

apiEndpointURL = "https://511mn.org/api/graphql"
camerasWithStreaming = []

body = [
    {
        "query": "query MapFeatures($input: MapFeaturesArgs!, $plowType: String) { mapFeaturesQuery(input: $input) { mapFeatures { bbox tooltip uri features { id geometry properties } __typename ... on Camera { views(limit: 5) { uri ... on CameraView { url } category } } ... on Plow { views(limit: 5, plowType: $plowType) { uri ... on PlowCameraView { url } category } } } error { message type } } }",
        "variables": {
            "input": {
                "north": 45.32945,
                "south": 44.69207,
                "east": -92.45245,
                "west": -93.85596,
                "zoom": 11,
                "layerSlugs": [
                    "normalCameras"
                ],
                "nonClusterableUris": [
                    "dashboard"
                ]
            },
            "plowType": "plowCameras"
        }
    }
]
r = requests.post(apiEndpointURL, json=body) 
json_data = r.json()

for i in json_data[0]['data']['mapFeaturesQuery']['mapFeatures']:
    try:
        camName = i['tooltip']
        camId = i['views'][0]['url'].split('/MN/')[1].split('?')[0]
        streamURL = f"https://video.dot.state.mn.us/public/{camId}.stream/playlist.m3u8"
        address = streamURL.split('https://')[1].split('/')[0]
        path = streamURL.split('https://video.dot.state.mn.us')[1]
        r2 = requests.head(streamURL)
        if r2.status_code == 200:
            print(f'This camera supports streaming! {camName}')
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
        else:
            print(f'This camera does not suppport streaming... {camName}')
    except:
        print("Ran into a exception when trying to import this camera, skipping...")

with open('cameras.json', 'w') as f:
    json.dump(camerasWithStreaming, f)

print(f"\n Amount of Cameras: {len(camerasWithStreaming)}")