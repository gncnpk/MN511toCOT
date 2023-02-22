# MN511 to CoT
### A PyTAK application that pulls cameras and road reports from 511mn.org and pushes it to TAK as a CoT Event.


## Installation

1. Install `pipenv` using `python -m pip install pipenv`
2. Run `python -m pipenv install` to install the prerequisites.
3. Create a `config.ini` and adjust the settings to your use-case.

## Usage/Setup

### Running (as a standalone service)

Run `python -m pipenv run python main.py` to start the application.

### Running (as a service)

1. Modify `mn511tocot.service` to the correct working directory, user, and shell script directory.
2. Copy it to the right directory using `cp mn511tocot.service /etc/systemd/system/`
3. Run `sudo systemctl daemon-reload`
4. Run `sudo systemctl enable mn511tocot` (if you want to run it at boot, otherwise skip this step)
5. Run `sudo systemctl start mn511tocot` to start the service

### Example Config
This config connects to TAK server instance via TLS (with a self-signed cert), pulls data and pushes CoT events every hour. This will only push cameras and not road reports.

`config.ini`
```ini
[mn511tocot]
COT_URL = tls://XX.XX.XX.XX:8089
PYTAK_TLS_CLIENT_CERT = private_key.pem
PYTAK_TLS_CLIENT_KEY = private_key.pem
PYTAK_TLS_DONT_VERIFY = true
POLL_INTERVAL = 3600
CAMS_ENABLED = true
ROAD_REPORTS_ENABLED = false
```
