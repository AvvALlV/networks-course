import socket

import requests
from requests import Request, utils, Response
import urllib3
import sys


class client:
    BUFFER_SIZE = 1024
    def __init__(self, server_host, server_port, request_filename):
        self.server_host = server_host
        self.server_port = server_port
        self.request_filename = request_filename
        pass

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((self.server_host, self.server_port))
            sock.sendall(self.prepare_request().encode())
            data = self.read_response(sock)
            self.handle_response(data)

    def read_response(self, sock):
        data = b''
        while True:
            part = sock.recv(self.BUFFER_SIZE)
            data += part
            if len(part) < self.BUFFER_SIZE:
                break
        return data

    def prepare_request(self):
        url = "/local/" + self.request_filename
        return f"""GET {url} HTTP/1.1"""

    def handle_response(self, data):
        data_pos = data.find(b'\r\n\r\n')
        headers = data[:data_pos].decode('utf-8').split('\r\n')
        status_line = headers[0].split(' ')

        if status_line[1] != '200':
            print(f"error: {' '.join(status_line[1:])}")
            return

        content = data[data_pos + 4:]

        if self.request_filename.endswith('.txt'):
            print(content.decode('utf-8'))

        with open(self.request_filename, 'wb') as file:
            file.write(content)

    def send_request(self):
        url = "http://" + self.server_host + ":" + str(self.server_port) + "/local"
        r = requests.get(url)
        print(r.status_code)

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("invalid number of arguments")
    else:
        client = client(sys.argv[1], int(sys.argv[2]), sys.argv[3])
        # client.send_request()
        client.start()
