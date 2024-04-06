import socket
import threading
import re

def sanitize_url(url):
    # Sanitizes URL to remove potentially harmful characters
    return re.sub(r'[^a-zA-Z0-9/:._-]', '', url)

def validate_request(method, path, version, headers):
    # Validates the HTTP method and version
    if method not in ['GET', 'POST', 'HEAD', 'PUT', 'DELETE', 'OPTIONS']:
        return False
    if version not in ['HTTP/1.1', 'HTTP/1.0']:
        return False
    return True

def parse_request(request_data):
    try:
        # Split the request data into lines
        lines = request_data.split('\r\n')
        # The request line is the first line
        request_line = lines[0]
        method, path, version = request_line.split(' ', 2)

        # Manually parse headers from the remaining lines until an empty line is encountered
        headers = {}
        for line in lines[1:]:
            if line == '':  # Stop at the first empty line; headers are done
                break
            header_name, header_value = line.split(': ', 1)
            headers[header_name] = header_value

        return method, path, version, headers
    except Exception as e:
        print(f"Error parsing request: {e}")
        return None, None, None, None


def forward_request_to_server(server_socket, method, path, version, headers, initial_line):
    # Creates and sends a new request to the target server
    server_socket.send(f"{method} {path} {version}\r\n".encode())

    # Forward headers to the target server
    for header, value in headers.items():
        server_socket.send(f"{header}: {value}\r\n".encode())
    server_socket.send("\r\n".encode())

def handle_client_connection(client_socket):
    keep_alive = True
    while keep_alive:
        try:
            request_data = client_socket.recv(4096).decode('utf-8')
            if not request_data:
                break

            method, path, version, headers = parse_request(request_data)
            if method is None:
                print("Failed to parse request. Closing connection.")
                break

            if not validate_request(method, path, version, headers):
                print("Invalid or unsafe request detected. Closing connection.")
                break

            keep_alive = headers.get('Connection') == 'keep-alive'

            # Determine the target server and port
            host = headers["Host"]
            if ':' in host:
                host, port = host.split(':', 1)
                port = int(port)
            else:
                port = 80

            # Establish a connection to the target server
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.connect((host, port))
            forward_request_to_server(server_socket, method, path, version, headers, request_data.split('\r\n', 1)[0])

            # Receive the response from the target server and forward it to the client
            while True:
                response_data = server_socket.recv(4096)
                if not response_data:
                    break
                client_socket.send(response_data)

            server_socket.close()
        except Exception as e:
            print(f"Error during connection handling: {e}")
            break

    try:
        client_socket.close()
    except Exception as e:
        print(f"Error closing client socket: {e}")

def start_proxy_server(port):
    try:
        listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen_socket.bind(('', port))
        listen_socket.listen(5)
        print(f'Proxy Server Listening on port {port}')
    except Exception as e:
        print(f"Failed to start proxy server: {e}")
        return

    while True:
        try:
            client_socket, address = listen_socket.accept()
            print(f'Accepted connection from {address}')
            client_thread = threading.Thread(target=handle_client_connection, args=(client_socket,))
            client_thread.start()
        except KeyboardInterrupt:
            print("Shutting down the proxy server.")
            break
        except Exception as e:
            print(f"Error accepting connection: {e}")

if __name__ == '__main__':
    PORT = 9876
    start_proxy_server(PORT)
