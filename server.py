import socket
import threading
import os
import base64
import random
import time
import struct

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

        # 获取文件大小并分配数据端口
        self.file_size = os.path.getsize(self.filename)
        data_port = self._allocate_data_port()
        if not data_port:
            return

        # 向客户端发送OK响应
        ok_msg = f"OK {self.filename} SIZE {self.file_size} PORT {data_port}"
        self.main_socket.sendto(ok_msg.encode(), self.client_addr)
        print(f"[SERVER] 发送OK响应: {ok_msg}")

        # 初始化数据传输套接字
        self.thread_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.thread_socket.bind(('0.0.0.0', data_port))
            print(f"[SERVER] 数据套接字绑定到端口 {data_port}")
            self._handle_data_transfer()
        except Exception as e:
            print(f"[SERVER] 数据套接字错误: {e}")
        finally:
            if self.thread_socket:
                self.thread_socket.close()

         