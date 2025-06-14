import socket
import threading
import os
import base64
import random
import time
import struct


class FileTransferThread(threading.Thread):
    def __init__(self, client_addr, main_socket, filename, port_range_start=50000, port_range_end=51000):
        super().__init__()
        self.client_addr = client_addr
        self.main_socket = main_socket
        self.filename = filename
        self.port_range_start = port_range_start
        self.port_range_end = port_range_end
        self.thread_socket = None
        self.file_size = 0
        self.chunk_size = 1000  # 每块最大1000字节二进制数据

    def run(self):
        # 检查文件是否存在
        if not os.path.exists(self.filename):
            error_msg = f"ERR {self.filename} NOT_FOUND"
            self.main_socket.sendto(error_msg.encode(), self.client_addr)
            return

    

