import os.path
import socket


class server_base:
    BUFFER_SIZE = 1024

    def __init__(self, port):
        self.port_ = port

    def read_request(self, conn, addr):
        data = b''
        while True:
            part = conn.recv(self.BUFFER_SIZE)
            data += part
            if len(part) < self.BUFFER_SIZE:
                break
        return data

    def handle_request(self, data):
        data = data.decode('utf-8').split("\r\n")
        request_line = data[0].split(" ")
        if len(request_line) != 3:
            return self.create_error_respose(400, "Bad request")

        if request_line[0] != "GET":
            return self.create_error_respose(400, "Bad request")

        filepath = os.path.curdir + request_line[1]
        if os.path.exists(filepath) and os.path.isfile(filepath):
            return self.create_success_response(filepath)

        return self.create_error_respose(404, "Not found")

    def create_error_respose(self, error_code, error_message):
        return f"HTTP/1.1 {error_code} {error_message}\r\n".encode()

    def create_success_response(self, filepath):
        content = b''
        with open(filepath, 'rb') as file:
            content = file.read()
        return f"HTTP/1.1 200\r\nContent-Length:{len(content)}\r\n\r\n".encode('utf-8') + content
