"""Main Flask application for server monitoring web interface."""
import os
import signal
import sys
from flask import Flask, render_template, jsonify
from metrics_collector import MetricsCollector
from config_loader import load_config, ConfigError

app = Flask(__name__)
collector = None


def format_metrics_for_display(metrics_dict: dict) -> list:
    """
    Format metrics dictionary for frontend display.
    
    Args:
        metrics_dict: Raw metrics dictionary from collector
        
    Returns:
        List of formatted server metrics
    """
    formatted = []
    
    for server_key, data in metrics_dict.items():
        server_info = {
            'name': data.get('name', 'Unknown'),
            'host': data.get('host', 'Unknown'),
            'status': data.get('status', 'error'),
            'error': data.get('error'),
            'timestamp': data.get('timestamp', 0)
        }
        
        if data.get('status') == 'success':
            # CPU
            cpu_usage = data.get('cpu_usage_percent')
            server_info['cpu_usage'] = f"{cpu_usage:.1f}%" if cpu_usage is not None else "N/A"
            
            # Memory
            memory = data.get('memory', {})
            if memory:
                mem_usage = memory.get('usage_percent', 0)
                mem_used = memory.get('used_mb', 0)
                mem_total = memory.get('total_mb', 0)
                server_info['memory_usage'] = f"{mem_usage:.1f}%"
                server_info['memory_detail'] = f"{mem_used}MB / {mem_total}MB"
            else:
                server_info['memory_usage'] = "N/A"
                server_info['memory_detail'] = "N/A"
            
            # Load Average
            load_avg = data.get('load_average', {})
            if load_avg:
                server_info['load_avg'] = f"{load_avg.get('1min', 0):.2f}"
            else:
                server_info['load_avg'] = "N/A"
            
            # Disk I/O
            disk_io = data.get('disk_io', {})
            if disk_io and 'read_mb' in disk_io:
                server_info['disk_io'] = f"R: {disk_io['read_mb']:.1f}MB W: {disk_io['write_mb']:.1f}MB"
            else:
                server_info['disk_io'] = "N/A"
            
            # Network I/O
            network_io = data.get('network_io', {})
            if network_io:
                server_info['network_io'] = f"RX: {network_io.get('rx_mb', 0):.1f}MB TX: {network_io.get('tx_mb', 0):.1f}MB"
            else:
                server_info['network_io'] = "N/A"
        else:
            # Error state
            server_info['cpu_usage'] = "Error"
            server_info['memory_usage'] = "Error"
            server_info['memory_detail'] = "Error"
            server_info['load_avg'] = "Error"
            server_info['disk_io'] = "Error"
            server_info['network_io'] = "Error"
        
        formatted.append(server_info)
    
    return formatted


@app.route('/')
def index():
    """Serve the main monitoring page."""
    return render_template('index.html')


@app.route('/api/metrics')
def get_metrics():
    """API endpoint to get current server metrics."""
    if collector is None:
        return jsonify({'error': 'Metrics collector not initialized'}), 500
    
    try:
        raw_metrics = collector.get_metrics()
        formatted_metrics = format_metrics_for_display(raw_metrics)
        return jsonify({
            'success': True,
            'metrics': formatted_metrics,
            'refresh_interval': collector.config.get('refresh_interval', 60)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    global collector
    if collector:
        collector.stop()
    sys.exit(0)


def main():
    """Main entry point for the application."""
    global collector
    
    # Load configuration
    try:
        config = load_config()
    except ConfigError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Initialize metrics collector
    try:
        collector = MetricsCollector()
        collector.start()
    except Exception as e:
        print(f"Failed to initialize metrics collector: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run Flask app
    port = config.get('port', 8080)
    app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == '__main__':
    main()

