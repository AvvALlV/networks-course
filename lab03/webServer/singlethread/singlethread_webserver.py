import socket
import sys
import server_base


class webserver(server_base.server_base):
    def __init__(self, port):
        super().__init__(port)

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(('', self.port_))
            sock.listen()
            while True:
                conn, addr = sock.accept()
                print('Connected by', addr)
                with conn:
                    request = self.read_request(conn, addr)
                    response = self.handle_request(request)
                    conn.sendall(response)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("invalid number of arguments: port must be specified")
    else:
        wb = webserver(int(sys.argv[1]))
        wb.start()
