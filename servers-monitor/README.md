# Server Monitoring Web Application

A web application that monitors multiple servers via SSH, collecting CPU, memory, load average, disk I/O, and network performance metrics. The application displays metrics in a sortable table and runs as a systemd service on Ubuntu.

## Features

- **SSH-based Monitoring**: Connects to remote servers via SSH using key-based authentication
- **Real-time Metrics**: Collects CPU usage, memory, load average, disk I/O, and network statistics
- **Web Interface**: Sortable table with auto-refresh functionality
- **Systemd Service**: Runs as a system service with automatic startup on boot
- **Error Handling**: Gracefully handles connection failures and timeouts
- **Configurable**: Easy configuration via JSON file

## Requirements

- Python 3.7 or higher
- Ubuntu Linux (for systemd service)
- SSH key-based access to monitored servers
- Required Python packages (see `requirements.txt`)

## Installation

### 1. Install Python Dependencies

```bash
cd /home/gadi/Cursor/servers-monitor
pip3 install -r requirements.txt
```

Or using a virtual environment (recommended):

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure the Application

Edit `config.json` to add your servers:

```json
{
  "servers": [
    {
      "name": "Web Server 1",
      "host": "192.168.1.10",
      "user": "ubuntu"
    },
    {
      "name": "DB Server",
      "host": "192.168.1.20",
      "user": "ubuntu"
    }
  ],
  "ssh_key_path": "/home/gadi/.ssh/id_rsa",
  "refresh_interval": 60,
  "port": 8080
}
```

**Configuration Options:**
- `servers`: Array of server objects, each with:
  - `name`: Display name for the server
  - `host`: IP address or hostname
  - `user`: SSH username
- `ssh_key_path`: Path to your SSH private key file
- `refresh_interval`: Collection interval in seconds (default: 60)
- `port`: Web server port (default: 8080)

### 3. Test SSH Connectivity

Ensure you can SSH to all configured servers using the specified key:

```bash
ssh -i /home/gadi/.ssh/id_rsa ubuntu@192.168.1.10
```

### 4. Test the Application

Run the application manually to verify it works:

```bash
python3 app.py
```

Then open your browser to `http://localhost:8080` (or the configured port).

Press `Ctrl+C` to stop the application.

## Systemd Service Setup

### 1. Update the Service File

Edit `servers-monitor.service` and update the paths if needed:

- `WorkingDirectory`: Should point to the application directory
- `ExecStart`: Should point to your Python interpreter and app.py
- `User`: Set to your username (or remove `User=%i` and set a specific user)

For example, if using a virtual environment:

```ini
ExecStart=/home/gadi/Cursor/servers-monitor/venv/bin/python /home/gadi/Cursor/servers-monitor/app.py
```

### 2. Install the Service

Copy the service file to systemd directory:

```bash
sudo cp servers-monitor.service /etc/systemd/system/
```

### 3. Reload Systemd

```bash
sudo systemctl daemon-reload
```

### 4. Enable and Start the Service

```bash
# Enable service to start on boot
sudo systemctl enable servers-monitor.service

# Start the service
sudo systemctl start servers-monitor.service
```

### 5. Check Service Status

```bash
# Check if service is running
sudo systemctl status servers-monitor.service

# View logs
sudo journalctl -u servers-monitor.service -f
```

### Service Management Commands

```bash
# Start service
sudo systemctl start servers-monitor.service

# Stop service
sudo systemctl stop servers-monitor.service

# Restart service
sudo systemctl restart servers-monitor.service

# Disable auto-start on boot
sudo systemctl disable servers-monitor.service

# View recent logs
sudo journalctl -u servers-monitor.service -n 50
```

## Usage

### Web Interface

Once the service is running, access the web interface at:

```
http://localhost:8080
```

(Replace `localhost` with your server's IP if accessing remotely, and `8080` with your configured port)

### Table Features

- **Sortable Columns**: Click any column header to sort by that column
- **Auto-refresh**: The table automatically refreshes at the configured interval
- **Status Indicators**: Green dot indicates successful data collection, red indicates errors
- **Error Display**: Failed connections show error messages in the Status column

## Metrics Collected

- **CPU Usage**: Percentage of CPU utilization
- **Memory Usage**: Memory usage percentage and details (used/total in MB)
- **Load Average**: 1-minute load average
- **Disk I/O**: Read and write statistics (if available)
- **Network I/O**: Receive and transmit statistics (if available)

## Troubleshooting

### Service Won't Start

1. Check service status:
   ```bash
   sudo systemctl status servers-monitor.service
   ```

2. Check logs for errors:
   ```bash
   sudo journalctl -u servers-monitor.service -n 100
   ```

3. Verify Python path in service file matches your system

4. Ensure configuration file is valid JSON:
   ```bash
   python3 -m json.tool config.json
   ```

### SSH Connection Failures

1. Verify SSH key path is correct in `config.json`
2. Test SSH connection manually:
   ```bash
   ssh -i /path/to/key user@host
   ```
3. Ensure SSH key has correct permissions:
   ```bash
   chmod 600 /path/to/ssh/key
   ```
4. Check that the SSH key is added to the remote server's `authorized_keys`

### No Metrics Displayed

1. Check if servers are reachable:
   ```bash
   ping <server-ip>
   ```
2. Verify SSH connectivity to each server
3. Check application logs for specific error messages
4. Ensure required commands are available on remote servers (`top`, `free`, `uptime`, etc.)

### Web Interface Not Accessible

1. Check if the service is running:
   ```bash
   sudo systemctl status servers-monitor.service
   ```
2. Verify the port is not in use:
   ```bash
   sudo netstat -tlnp | grep 8080
   ```
3. Check firewall settings if accessing remotely
4. Verify the port in `config.json` matches what you're trying to access

## File Structure

```
servers-monitor/
├── app.py                 # Main Flask application
├── ssh_client.py          # SSH connection and command execution
├── metrics_collector.py   # Metrics collection logic
├── config_loader.py       # Configuration loading and validation
├── config.json            # Configuration file
├── requirements.txt       # Python dependencies
├── servers-monitor.service # Systemd service file
├── templates/
│   └── index.html         # Web frontend
├── static/
│   └── style.css          # CSS styling
└── README.md              # This file
```

## Security Considerations

- The application uses SSH key-based authentication (no passwords)
- Ensure SSH keys have appropriate permissions (600)
- Consider running the service as a non-root user
- If exposing the web interface externally, consider adding authentication
- Keep SSH keys secure and rotate them regularly

## License

This project is provided as-is for monitoring purposes.

