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

    def _allocate_data_port(self):
        """分配50000-51000范围内的可用端口"""
        for _ in range(100):  # 最多尝试100次
            port = random.randint(self.port_range_start, self.port_range_end)
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                test_socket.bind(('0.0.0.0', port))
                test_socket.close()
                return port
            except:
                test_socket.close()
        print(f"[SERVER] 无法分配可用端口")
        return None

    def _handle_data_transfer(self):
        """处理客户端的数据块请求"""
        with open(self.filename, 'rb') as file:
            while True:
                try:
                    # 接收客户端的文件块请求
                    request, client_data_addr = self.thread_socket.recvfrom(4096)
                    request = request.decode('utf-8')
                    print(f"[SERVER] 收到数据请求: {request} from {client_data_addr}")

                    # 解析请求格式: FILE <filename> GET START <start> END <end>
                    parts = request.split()
                    if (len(parts) >= 7 and parts[0] == 'FILE' and parts[1] == self.filename and
                            parts[2] == 'GET' and parts[3] == 'START' and parts[5] == 'END'):
                        start = int(parts[4])
                        end = int(parts[6])

                        # 读取文件块并发送响应
                        file.seek(start)
                        data = file.read(end - start + 1)
                        encoded_data = base64.b64encode(data).decode('utf-8')

                        response = f"FILE {self.filename} OK START {start} END {end} DATA {encoded_data}"
                        self.thread_socket.sendto(response.encode('utf-8'), client_data_addr)
                        print(f"[SERVER] 发送数据块 {start}-{end}，大小: {len(data)}字节")

                        # 检查是否发送完所有数据
                        if end >= self.file_size - 1:
                            print(f"[SERVER] 文件 {self.filename} 传输完成")
                            break

                    # 处理关闭请求
                    elif len(parts) >= 3 and parts[0] == 'FILE' and parts[1] == self.filename and parts[2] == 'CLOSE':
                        close_msg = f"FILE {self.filename} CLOSE_OK"
                        self.thread_socket.sendto(close_msg.encode('utf-8'), client_data_addr)
                        print(f"[SERVER] 发送关闭确认: {close_msg}")
                        break

                except Exception as e:
                    print(f"[SERVER] 数据传输错误: {e}")
                    break


