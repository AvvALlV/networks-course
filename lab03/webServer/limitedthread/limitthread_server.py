from server_base import server_base
import sys
import socket
import threading
from multiprocessing.pool import ThreadPool


class webserver(server_base):
    pool = ThreadPool(10)

    def __init__(self, port, corrency_level):
        self.semaphore = threading.Semaphore(corrency_level)
        super(webserver, self).__init__(port)

    def start(self):
        with self.pool:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('', self.port_))
                sock.listen()
                while True:
                    conn, addr = sock.accept()
                    print('Connected by', addr)
                    threading.Thread(target=self.handle_client, args=(conn, addr)).start()

    def handle_client(self, conn, addr):
        with self.semaphore:
            with conn:
                request = self.read_request(conn, addr)
                response = self.pool.apply(self.handle_request, args=(request,))
                conn.sendall(response)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("invalid number of arguments: port must be specified")
    else:
        wb = webserver(int(sys.argv[1]), int(sys.argv[2]))
        wb.start()
