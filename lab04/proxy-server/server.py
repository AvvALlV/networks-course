import logging
import socket
import threading
from multiprocessing.pool import ThreadPool
from datetime import datetime
import requests
from pathlib import Path
import os
import json
import sys


class cache_t:
    mutex = threading.Lock()
    cache_storage_path = Path('./cache_storage/')
    cache_info_path = cache_storage_path / 'cache_info.json'

    def __init__(self):
        if not self.cache_info_path.exists():
            with open(self.cache_info_path, 'w+') as cache_info_file:
                json.dump([], cache_info_file)

    def push_cache(self, document_info, content):
        with self.mutex:
            with open(self.cache_info_path, mode='r+') as file:
                cache_info = json.load(file)
                for document in cache_info:
                    self.remove_by_time_cache(cache_info, document)

                doc_filepath = self.cache_storage_path / document_info['ETag']
                if not doc_filepath.exists():
                    os.makedirs(os.path.dirname(doc_filepath), exist_ok=True)
                with open(doc_filepath, mode='wb+') as document_file:
                    document_file.write(content)
                cache_info.append(document_info)

                file.truncate(0)
                file.seek(0)
                json.dump(cache_info, file)

    def remove_by_time_cache(self, total_info, document_info):
        date_time = datetime.strptime(document_info['Date'], "%a, %d %b %Y %H:%M:%S %Z")
        if 'Cache-Control' in document_info and 'max-age' in document_info['Cache-Control'] and (
                datetime.now() - date_time).total_seconds() > \
                int(document_info['Cache-Control']['max-age']):
            total_info.remove(document_info)
            os.remove(self.cache_storage_path / document_info['ETag'])
            return True
        return False

    def remove_cache(self, url):
        with self.mutex:
            with open(file=self.cache_info_path, mode='r+') as file:
                cache_info = json.load(file)
                for document in cache_info:
                    if document['url'] == url:
                        cache_info.remove(document)
                        os.remove(self.cache_storage_path / document['ETag'])
                file.truncate(0)
                file.seek(0)
                json.dump(cache_info, file)

    def update_cache(self, document_info, new_content):
        with self.mutex:
            with open(file=self.cache_info_path, mode='r+') as file:
                cache_info = json.load(file)
                for i, document in enumerate(cache_info):
                    if document['url'] == document_info['url']:
                        cache_info[i] = document_info
                        with open(self.cache_storage_path / document_info['ETag'], mode='wb') as document_file:
                            document_file.write(new_content)
                file.truncate(0)
                file.seek(0)
                json.dump(cache_info, file)

    def contains(self, url):
        with self.mutex:
            with open(file=self.cache_info_path, mode='r+') as file:
                cache_info = json.load(file)
                for document in cache_info:
                    if document['url'] == url and not self.remove_by_time_cache(cache_info, document):
                        with open(self.cache_storage_path / document['ETag'], mode='br+') as document_file:
                            return document, document_file.read()
            return None, None


class base_proxy_server:
    pool = ThreadPool(10)
    BUFFER_SIZE = 1024

    def __init__(self, port):
        self.port_ = port

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(('', self.port_))
            sock.listen()
            while True:
                (conn, addr) = sock.accept()
                threading.Thread(target=self.handle_client, args=(conn, addr)).start()

    def handle_client(self, conn, addr):
        with conn:
            request = self.read_request(conn, addr)
            response_data = self.pool.apply(self.handle_request, args=(request,))
            conn.sendall(response_data)

    def handle_request(self, request):
        pass

    def read_request(self, conn, addr):
        data = b''
        while True:
            part = conn.recv(self.BUFFER_SIZE)
            data += part
            if len(part) < self.BUFFER_SIZE:
                break
        return data

    def parse_headers(self, raw_headers):
        headers = {}
        for i, field in enumerate(raw_headers):
            if len(field) == 0 and len(raw_headers) > i + 1:
                return headers, raw_headers[i + 1]
            key, value = field.split(b": ", 1)
            headers[key.decode()] = value.decode()
        return headers, None

    def create_response(self, code, message='', body=None):
        response = f"HTTP/1.1 {code} {message}\r\n"
        if body is not None:
            response += f'Content-Length: {len(body)}\r\n'
            return (response + '\r\n').encode() + body
        return response.encode()


class proxy_server(base_proxy_server):

    def __init__(self, port):
        super().__init__(port)

    def handle_request(self, request):
        request = request.split(b"\r\n")
        request_line = request[0].decode().split(" ")
        url = request_line[1][1:]
        headers, content = self.parse_headers(request[1:])
        try:
            request, response = f"http://{url}", None
            if 'Referer' in headers.keys():
                request = f'{headers["Referer"]}/{url}'
            if request_line[0] == "GET":
                response = requests.get(request)
            if request_line[0] == "POST":
                response = requests.post(request, data=content)
            logging.info(f"{request[0]}: {response.status_code}")
            return self.create_response(response.status_code, response.reason, response.content)
        except Exception as e:
            logging.error(f"{request[0]}: {e}")
            return self.create_response(404, "not found")


def create_cache_object(url, response: requests.Response):
    if 'ETag' not in response.headers:
        return None
    result = {'url': url, 'Date': response.headers['Date'], 'ETag': response.headers['ETag']}
    if 'Last-Modified' in response.headers:
        result['Last-Modified'] = response.headers['Last-Modified']
    if 'Cache-Control' in response.headers:
        control = {}
        for cache_value in response.headers['Cache-Control'].split(', '):
            if cache_value.startswith('max-age='):
                key, value = cache_value.split('=', 1)
                control[key] = value
        result['Cache-Control'] = control
    return result


class cached_proxy_server(base_proxy_server):
    cache = cache_t()
    black_list_path = Path('./blacklist.txt')

    def __init__(self, port, black_list=False):
        self.black_list = None
        if black_list:
            with open(self.black_list_path, 'r') as f:
                self.black_list = [line.strip() for line in f]
        super().__init__(port)

    def handle_request(self, request):
        if len(request) == 0:
            return b''

        request = request.split(b"\r\n")
        request_line = request[0].decode().split(" ")
        url = request_line[1][1:]
        if self.black_list and url in self.black_list:
            logging.info(f"{url}: blacklisted source")
            return self.create_response(403, "blacklisted source",
                                        b"<!DOCTYPE html><html><body><h1>blacklisted source</h1></body></html>")

        headers, content = self.parse_headers(request[1:])
        try:
            new_request, response = f"http://{url}", None
            if 'Referer' in headers.keys():
                new_request = f'{headers["Referer"]}/{url}'

            print(new_request)
            if request_line[0] == "GET":
                document_info, content = self.cache.contains(url)
                if document_info is not None:
                    if 'Last-Modified' in document_info:
                        response = requests.get(new_request,
                                                headers={'If-Modified-Since': document_info['Last-Modified'],
                                                         'If-None-Match': document_info['ETag']})
                    if 'Last-Modified' not in document_info or response.status_code == 304:
                        logging.info(f"{request[0]}: from cache")
                        return self.create_response(200, '', content)

                    doc = create_cache_object(url, response)
                    if doc:
                        self.cache.update_cache(doc, response.content)

                else:
                    response = requests.get(new_request)
                    doc = create_cache_object(url, response)
                    if doc:
                        self.cache.push_cache(doc, response.content)

            if request_line[0] == "POST":
                response = requests.post(request, data=content)

            logging.info(f"{request[0]}: {response.status_code}")
            return self.create_response(response.status_code, response.reason, response.content)
        except Exception as e:
            logging.error(f"{request[0]}: {e}")
            return self.create_response(404, "not found")


if __name__ == '__main__':
    logging.basicConfig(filename='cache_request_log.log', format='%(levelname)s:%(message)s', encoding='utf-8',
                        level=logging.INFO)
    server = None
    port = int(sys.argv[1])
    if sys.argv[2] == '--cached':
        blacklist = len(sys.argv) == 4 and sys.argv[3] == '--blacklist'
        server = cached_proxy_server(port, blacklist)
    else:
        server = proxy_server(port)
    server.start()
