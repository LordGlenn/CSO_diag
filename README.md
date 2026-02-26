# CSO Diagnostics Collector

Command-line tool for collecting diagnostics files from Zyxel USG Flex H series devices.

The tool automates the entire process: login to the device web UI, trigger diagnostics collection, wait for completion, and download the resulting file — all in one command.

## Download

Pre-built binaries for macOS and Windows are available on the [Releases](https://github.com/LordGlenn/CSO_diag/releases) page.

Download the zip for your platform, extract it, and run the executable directly. No Python or other dependencies required.

### macOS First Run

macOS will block the downloaded executable because it is not signed by Apple. After extracting the zip, run the following command once to remove the quarantine flag:

```bash
xattr -cr cso_diag/
```

Then you can run `./cso_diag/cso_diag` normally.

## Usage

```
cso_diag <device_ip> <username> <password> [options]
```

### Arguments

| Argument     | Description                          |
|-------------|--------------------------------------|
| `device_ip` | Device IP address (e.g. 192.168.1.1) |
| `username`  | Admin username                       |
| `password`  | Admin password                       |

### Options

| Option              | Description                                        | Default |
|--------------------|----------------------------------------------------|---------|
| `-p`, `--port`       | Device HTTPS port                                  | `443`   |
| `-o`, `--output-dir` | Output directory for downloaded file               | `.`     |
| `-t`, `--timeout`    | Max wait time in seconds for collection            | `1800`  |

### Examples

```bash
# Basic usage
./cso_diag 192.168.1.1 admin mypassword

# Save to a specific directory
./cso_diag 192.168.1.1 admin mypassword -o /tmp/diagnostics

# Connect to a non-standard HTTPS port
./cso_diag 192.168.1.1 admin mypassword -p 8443

# Set a custom timeout (60 minutes)
./cso_diag 192.168.1.1 admin mypassword -t 3600
```

### Sample Output

```
[cso_diag] Launching browser...
[cso_diag] Connecting to https://192.168.1.1 ...
[cso_diag] Login page loaded. Logging in...
[cso_diag] Login successful. Navigating to Diagnostics...
[cso_diag] Diagnostics page loaded.
[cso_diag] Starting diagnostics collection...
[cso_diag] Collecting... (0s elapsed, timeout in 1800s)
[cso_diag] Collecting... (10s elapsed, timeout in 1790s)
...
[cso_diag] Collection complete!
[cso_diag] File ready: diaginfo-2026-02-25_14-45-03.tar.bz2 (73.5 MB)
[cso_diag] Selecting file and starting download...
[cso_diag] Download complete: ./diaginfo-2026-02-25_14-45-03.tar.bz2
[cso_diag] File size: 73.5 MB
[cso_diag] Done!
```

## Run from Source

Requires Python 3.9+ and Playwright.

```bash
pip install playwright
python -m playwright install chromium
python cso_diag.py 192.168.1.1 admin mypassword
```

## Build from Source

### macOS / Linux

```bash
chmod +x build.sh
./build.sh
```

### Windows

```cmd
build.bat
```

The packaged output will be in `dist/cso_diag/`. Distribute the entire directory as a zip.

## How It Works

1. Launches a headless Chromium browser via Playwright
2. Logs into the device web management UI (`/weblogin.cgi`)
3. Navigates to **Maintenance > Diagnostics**
4. Clicks **Collect Now** to start diagnostics collection
5. Polls the status every 10 seconds until collection completes
6. Selects the generated file and downloads it via the web UI
7. Saves the `.tar.bz2` file to the specified output directory

## Supported Devices

- Zyxel USG FLEX 50H
- Zyxel USG FLEX 100H
- Zyxel USG FLEX 200H
- Zyxel USG FLEX 500H
- Zyxel USG FLEX 700H

## License

MIT
