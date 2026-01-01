"""Metrics collector for gathering server performance data via SSH."""
import re
import threading
import time
from typing import Dict, List, Optional, Any
from ssh_client import SSHClient
from config_loader import load_config


class MetricsCollector:
    """Collects performance metrics from multiple servers via SSH."""
    
    def __init__(self, config_path: str = "config.json"):
        """
        Initialize metrics collector.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = load_config(config_path)
        self.metrics = {}
        self.lock = threading.Lock()
        self.running = False
        self.collection_thread = None
    
    def _parse_cpu_usage(self, output: str) -> Optional[float]:
        """Parse CPU usage percentage from command output."""
        # Try to parse from top command
        match = re.search(r'%Cpu\(s\):\s+(\d+\.?\d*)', output)
        if match:
            return float(match.group(1))
        
        # Try to parse from /proc/stat format
        # This is more complex and would require calculating idle time
        # For simplicity, we'll use a simpler approach
        match = re.search(r'cpu\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', output)
        if match:
            # Basic calculation - this is simplified
            return None  # Would need more complex parsing
        
        return None
    
    def _get_cpu_usage(self, ssh: SSHClient) -> Optional[float]:
        """Get CPU usage percentage."""
        # Try top command first
        success, output, _ = ssh.execute_command("top -bn1 | grep 'Cpu(s)' | head -1")
        if success and output:
            match = re.search(r'(\d+\.?\d*)%us', output)
            if match:
                return float(match.group(1))
        
        # Fallback to /proc/stat calculation
        success, output, _ = ssh.execute_command(
            "grep '^cpu ' /proc/stat | awk '{usage=($2+$4)*100/($2+$3+$4+$5)} END {print usage}'"
        )
        if success and output:
            try:
                return float(output.strip())
            except ValueError:
                pass
        
        return None
    
    def _get_memory_usage(self, ssh: SSHClient) -> Optional[Dict[str, Any]]:
        """Get memory usage statistics."""
        success, output, _ = ssh.execute_command("free -m")
        if not success:
            return None
        
        # Parse free output
        lines = output.split('\n')
        if len(lines) < 2:
            return None
        
        # Parse Mem line: Mem:    total    used    free    shared  buff/cache   available
        mem_line = lines[1]
        parts = mem_line.split()
        if len(parts) < 7:
            return None
        
        try:
            total = int(parts[1])
            used = int(parts[2])
            free = int(parts[3])
            available = int(parts[6]) if len(parts) > 6 else used
            
            return {
                'total_mb': total,
                'used_mb': used,
                'free_mb': free,
                'available_mb': available,
                'usage_percent': (used / total * 100) if total > 0 else 0
            }
        except (ValueError, IndexError):
            return None
    
    def _get_load_average(self, ssh: SSHClient) -> Optional[Dict[str, float]]:
        """Get load average."""
        success, output, _ = ssh.execute_command("uptime")
        if success and output:
            # Parse: load average: 0.52, 0.58, 0.59
            match = re.search(r'load average:\s+([\d.]+),\s+([\d.]+),\s+([\d.]+)', output)
            if match:
                try:
                    return {
                        '1min': float(match.group(1)),
                        '5min': float(match.group(2)),
                        '15min': float(match.group(3))
                    }
                except ValueError:
                    pass
        
        # Fallback to /proc/loadavg
        success, output, _ = ssh.execute_command("cat /proc/loadavg")
        if success and output:
            parts = output.strip().split()
            if len(parts) >= 3:
                try:
                    return {
                        '1min': float(parts[0]),
                        '5min': float(parts[1]),
                        '15min': float(parts[2])
                    }
                except ValueError:
                    pass
        
        return None
    
    def _get_disk_io(self, ssh: SSHClient) -> Optional[Dict[str, Any]]:
        """Get disk I/O statistics."""
        # Try iostat first
        success, output, _ = ssh.execute_command("iostat -x 1 1 2>/dev/null | tail -n +4")
        if success and output:
            # Parse iostat output (simplified)
            lines = output.strip().split('\n')
            if lines:
                # This is a simplified parser - real iostat has more columns
                return {'status': 'available', 'details': 'iostat'}
        
        # Fallback to /proc/diskstats
        success, output, _ = ssh.execute_command(
            "cat /proc/diskstats | grep -E 'sd[a-z]|nvme|vd[a-z]' | head -1 | "
            "awk '{read=$6*512/1024/1024; write=$10*512/1024/1024; print read\" \"write}'"
        )
        if success and output:
            parts = output.strip().split()
            if len(parts) >= 2:
                try:
                    return {
                        'read_mb': float(parts[0]),
                        'write_mb': float(parts[1])
                    }
                except ValueError:
                    pass
        
        return {'status': 'unavailable'}
    
    def _get_network_io(self, ssh: SSHClient) -> Optional[Dict[str, Any]]:
        """Get network I/O statistics."""
        # Get network stats from /proc/net/dev
        success, output, _ = ssh.execute_command(
            "cat /proc/net/dev | grep -E 'eth0|ens|enp|wlan' | head -1 | "
            "awk '{rx=$2/1024/1024; tx=$10/1024/1024; print rx\" \"tx}'"
        )
        if success and output:
            parts = output.strip().split()
            if len(parts) >= 2:
                try:
                    return {
                        'rx_mb': float(parts[0]),
                        'tx_mb': float(parts[1])
                    }
                except ValueError:
                    pass
        
        return None
    
    def _collect_server_metrics(self, server: Dict[str, str]) -> Dict[str, Any]:
        """
        Collect metrics from a single server.
        
        Args:
            server: Server configuration dictionary
            
        Returns:
            Dictionary containing server metrics or error information
        """
        result = {
            'name': server['name'],
            'host': server['host'],
            'timestamp': time.time(),
            'status': 'error',
            'error': None
        }
        
        ssh = SSHClient(
            host=server['host'],
            user=server['user'],
            key_path=self.config['ssh_key_path']
        )
        
        try:
            connect_success, connect_error = ssh.connect()
            if not connect_success:
                result['error'] = connect_error or 'SSH connection failed'
                return result
            
            # Collect all metrics with individual error handling
            try:
                cpu_usage = self._get_cpu_usage(ssh)
            except Exception as e:
                cpu_usage = None
                # Continue collecting other metrics even if one fails
            
            try:
                memory = self._get_memory_usage(ssh)
            except Exception as e:
                memory = None
            
            try:
                load_avg = self._get_load_average(ssh)
            except Exception as e:
                load_avg = None
            
            try:
                disk_io = self._get_disk_io(ssh)
            except Exception as e:
                disk_io = None
            
            try:
                network_io = self._get_network_io(ssh)
            except Exception as e:
                network_io = None
            
            result.update({
                'status': 'success',
                'cpu_usage_percent': cpu_usage,
                'memory': memory,
                'load_average': load_avg,
                'disk_io': disk_io,
                'network_io': network_io
            })
            
        except Exception as e:
            result['error'] = f"Unexpected error collecting metrics: {str(e)}"
        finally:
            try:
                ssh.close()
            except Exception:
                pass  # Ignore errors during cleanup
        
        return result
    
    def collect_all_metrics(self):
        """Collect metrics from all configured servers."""
        results = {}
        
        for server in self.config['servers']:
            server_key = f"{server['name']}_{server['host']}"
            results[server_key] = self._collect_server_metrics(server)
        
        with self.lock:
            self.metrics = results
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current metrics (thread-safe).
        
        Returns:
            Dictionary of all server metrics
        """
        with self.lock:
            return self.metrics.copy()
    
    def _collection_loop(self):
        """Background thread loop for periodic metric collection."""
        while self.running:
            try:
                self.collect_all_metrics()
            except Exception as e:
                # Log error but continue running
                print(f"Error in collection loop: {e}", flush=True)
            
            # Sleep with interruption check
            sleep_time = self.config['refresh_interval']
            elapsed = 0
            while self.running and elapsed < sleep_time:
                time.sleep(min(1, sleep_time - elapsed))
                elapsed += 1
    
    def start(self):
        """Start background metric collection."""
        if self.running:
            return
        
        self.running = True
        # Do initial collection
        self.collect_all_metrics()
        # Start background thread
        self.collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
        self.collection_thread.start()
    
    def stop(self):
        """Stop background metric collection."""
        self.running = False
        if self.collection_thread:
            self.collection_thread.join(timeout=5)

