"""SSH client module for executing remote commands on servers."""
import paramiko
import os
import socket
from typing import Optional, Tuple


class SSHClient:
    """SSH client for connecting to remote servers and executing commands."""
    
    def __init__(self, host: str, user: str, key_path: str, timeout: int = 10):
        """
        Initialize SSH client.
        
        Args:
            host: Server hostname or IP address
            user: SSH username
            key_path: Path to SSH private key file
            timeout: Connection timeout in seconds
        """
        self.host = host
        self.user = user
        self.key_path = key_path
        self.timeout = timeout
        self.client = None
    
    def connect(self) -> Tuple[bool, Optional[str]]:
        """
        Establish SSH connection to the server.
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            if not os.path.exists(self.key_path):
                return False, f"SSH key file not found: {self.key_path}"
            
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            try:
                private_key = paramiko.RSAKey.from_private_key_file(self.key_path)
                self.client.connect(
                    hostname=self.host,
                    username=self.user,
                    pkey=private_key,
                    timeout=self.timeout,
                    look_for_keys=False,
                    allow_agent=False
                )
                return True, None
            except paramiko.AuthenticationException:
                return False, "SSH authentication failed - check key and permissions"
            except paramiko.BadHostKeyException:
                return False, "SSH host key verification failed"
            except paramiko.SSHException as e:
                return False, f"SSH connection error: {str(e)}"
            except socket.timeout:
                return False, f"Connection timeout after {self.timeout} seconds"
            except socket.gaierror:
                return False, f"Could not resolve hostname: {self.host}"
            except Exception as e:
                return False, f"Unexpected error: {str(e)}"
        except Exception as e:
            return False, f"Failed to initialize SSH client: {str(e)}"
    
    def execute_command(self, command: str) -> Tuple[bool, str, str]:
        """
        Execute a command on the remote server.
        
        Args:
            command: Command to execute
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        if not self.client:
            return False, "", "Not connected to server"
        
        if not self.client.get_transport() or not self.client.get_transport().is_active():
            return False, "", "SSH connection is not active"
        
        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=self.timeout)
            exit_status = stdout.channel.recv_exit_status()
            
            try:
                stdout_text = stdout.read().decode('utf-8', errors='replace').strip()
            except Exception:
                stdout_text = ""
            
            try:
                stderr_text = stderr.read().decode('utf-8', errors='replace').strip()
            except Exception:
                stderr_text = ""
            
            if exit_status != 0:
                error_msg = stderr_text if stderr_text else f"Command failed with exit code {exit_status}"
                return False, stdout_text, error_msg
            
            return True, stdout_text, stderr_text
        except socket.timeout:
            return False, "", f"Command timeout after {self.timeout} seconds"
        except paramiko.SSHException as e:
            return False, "", f"SSH error executing command: {str(e)}"
        except Exception as e:
            return False, "", f"Error executing command: {str(e)}"
    
    def close(self):
        """Close SSH connection."""
        if self.client:
            self.client.close()
            self.client = None
    
    def __enter__(self):
        """Context manager entry."""
        success, error = self.connect()
        if not success:
            raise ConnectionError(error or "Failed to connect")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

