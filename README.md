# dashcam-downloader

Background downloader for BlackVue dashcam recordings.

The service polls the dashcam VOD index, parses completed recording entries, and downloads each video file to local storage. Downloads happen in a separate worker thread so polling can continue while files are transferring.

## Overview

The dashcam index at `http://192.168.68.17/blackvue_vod.cgi` returns entries like:

```text
v:1.00
n:/Record/20260602_074033_PF.mp4,s:1000000
n:/Record/20260602_074130_PF.mp4,s:1000000
```

`n:` is the file path on the dashcam. `s:1000000` is the complete-file marker and means the camera has finished writing the clip. Entries without `s:1000000` are skipped until a later poll.

## Configuration

Copy the example configuration file:

```bash
cp config/app.env.example config/app.env
```

Edit `config/app.env` as needed:

| Variable | Description | Default |
|----------|-------------|---------|
| `DASHCAM_BASE_URL` | Base URL for the dashcam | `http://192.168.68.17` |
| `DASHCAM_INDEX_PATH` | VOD index path | `/blackvue_vod.cgi` |
| `DOWNLOAD_DIR` | Local download root | `/downloads` |
| `POLL_INTERVAL_SECONDS` | Poll interval in seconds | `60` |
| `COMPLETE_FILE_SIZE` | Size marker for complete files | `1000000` |
| `REQUEST_TIMEOUT_SECONDS` | HTTP request timeout | `30` |
| `DOWNLOAD_RETRIES` | Retries after an initial failed transfer | `3` |
| `RETRY_DELAY_SECONDS` | Delay between download retries | `10` |
| `QUEUE_MAX_SIZE` | Maximum queued downloads | `1000` |
| `LOG_LEVEL` | Logging level | `INFO` |

Downloaded files preserve the dashcam path under `DOWNLOAD_DIR`, for example:

```text
/downloads/Record/20260602_074033_PF.mp4
```

## Running Locally

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp config/app.env.example config/app.env
python -m src.main
```

## Running with Docker

```bash
docker compose up -d --build
docker compose logs -f
docker compose down
```

The compose file uses host networking so the container can reach the dashcam on the LAN.

## Safety

- The service does not delete recordings from the dashcam.
- Only `/Record/...` paths are accepted.
- Unsafe or non-normalized paths are rejected before disk writes.
- Downloads are written to `.part` files and atomically renamed after the HTTP transfer completes.
- Existing completed local files are skipped.

## Tests

```bash
python -m pytest
docker compose config --quiet
```

## Project Structure

```text
dashcam-downloader/
├── .github/workflows/deploy.yml
├── config/
│   └── app.env.example
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── constants.py
│   ├── downloader.py
│   ├── index_parser.py
│   └── main.py
├── tests/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```
