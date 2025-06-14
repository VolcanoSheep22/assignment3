import socket
import os
import base64
import time
import struct
import threading


class UDPClient:
    def __init__(self, server_host, server_port, download_list_file):
        self.server_host = server_host
        self.server_port = server_port
        self.download_list_file = download_list_file
        self.main_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.timeout_base = 0.5  # 初始超时时间(秒)
        self.max_retries = 5  # 最大重传次数
        self.chunk_size = 1000  # 每块最大1000字节二进制数据

    def send_and_receive(self, message, target_addr, retries=0):
        """发送消息并接收响应，包含超时重传机制"""
        if retries > self.max_retries:
            print(f"[CLIENT] 重传次数超过限制，放弃请求")
            return None

        timeout = self.timeout_base * (2 ** retries)  # 指数退避
        self.main_socket.settimeout(timeout)

        try:
            self.main_socket.sendto(message.encode('utf-8'), target_addr)
            print(f"[CLIENT] 发送: {message} 到 {target_addr}，超时: {timeout}秒")

            while True:
                try:
                    response, addr = self.main_socket.recvfrom(4096)
                    response = response.decode('utf-8')
                    print(f"[CLIENT] 接收: {response} 来自 {addr}")
                    return response
                except socket.timeout:
                    if retries < self.max_retries:
                        print(f"[CLIENT] 超时，重试 {retries + 1}/{self.max_retries}")
                        self.main_socket.sendto(message.encode('utf-8'), target_addr)
                    else:
                        raise
        except Exception as e:
            print(f"[CLIENT] 通信错误: {e}")
            return None

    def download_file(self, filename, data_port):
        """从指定端口下载单个文件"""
        print(f"[CLIENT] 开始下载文件: {filename}")
        data_addr = (self.server_host, data_port)
        downloaded_size = 0
        file_path = os.path.join(os.getcwd(), filename)

        # 创建数据套接字（客户端无需绑定，每次发送时指定目标地址）
        data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        data_socket.settimeout(self.timeout_base)

        try:
            with open(file_path, 'wb') as file:
                # 分块请求数据
                start = 0
                while True:
                    end = min(start + self.chunk_size - 1, os.path.getsize(filename) - 1)
                    request = f"FILE {filename} GET START {start} END {end}"

                    # 发送数据块请求并接收响应
                    response = self.send_and_receive(request, data_addr)
                    if not response:
                        break

                    # 解析响应
                    parts = response.split()
                    if (len(parts) >= 9 and parts[0] == 'FILE' and parts[1] == filename and
                            parts[2] == 'OK' and parts[3] == 'START' and parts[5] == 'END' and parts[7] == 'DATA'):
                        resp_start = int(parts[4])
                        resp_end = int(parts[6])
                        encoded_data = ' '.join(parts[8:])

                        # 验证字节范围
                        if resp_start == start and resp_end == end:
                            data = base64.b64decode(encoded_data)
                            file.write(data)
                            downloaded_size += len(data)
                            start = end + 1

                            # 显示下载进度
                            progress = '*' * (downloaded_size // 1000)
                            print(f"[CLIENT] 下载进度: {downloaded_size}/{os.path.getsize(filename)} 字节 {progress}")

                            # 检查是否完成下载
                            if end >= os.path.getsize(filename) - 1:
                                print(f"[CLIENT] 下载完成: {filename}")
                                break
                        else:
                            print(f"[CLIENT] 字节范围不匹配，期望 {start}-{end}，收到 {resp_start}-{resp_end}")
                    else:
                        print(f"[CLIENT] 无效的响应格式: {response}")

            # 发送关闭请求
            close_msg = f"FILE {filename} CLOSE"
            close_response = self.send_and_receive(close_msg, data_addr)
            if close_response and close_response.startswith(f"FILE {filename} CLOSE_OK"):
                print(f"[CLIENT] 连接关闭确认已接收")
            else:
                print(f"[CLIENT] 未收到连接关闭确认")

        except Exception as e:
            print(f"[CLIENT] 下载文件 {filename} 时出错: {e}")
        finally:
            data_socket.close()
        return downloaded_size == os.path.getsize(filename)

    def process_download_list(self):
        """处理下载列表文件中的所有文件"""
        if not os.path.exists(self.download_list_file):
            print(f"[CLIENT] 下载列表文件不存在: {self.download_list_file}")
            return

        with open(self.download_list_file, 'r') as file:
            filenames = [line.strip() for line in file if line.strip()]

        if not filenames:
            print(f"[CLIENT] 下载列表文件为空")
            return

        print(f"[CLIENT] 待下载文件: {filenames}")

        # 逐个下载文件
        for filename in filenames:
            # 发送DOWNLOAD请求
            download_msg = f"DOWNLOAD {filename}"
            main_addr = (self.server_host, self.server_port)
            response = self.send_and_receive(download_msg, main_addr)

            if not response:
                print(f"[CLIENT] 未收到服务器响应，跳过文件: {filename}")
                continue

            # 解析响应
            if response.startswith(f"OK {filename}"):
                parts = response.split()
                if len(parts) >= 7 and parts[3] == 'SIZE' and parts[5] == 'PORT':
                    file_size = int(parts[4])
                    data_port = int(parts[6])
                    print(f"[CLIENT] 服务器响应: 文件大小 {file_size} 字节，数据端口 {data_port}")

                    # 下载文件
                    success = self.download_file(filename, data_port)
                    if success:
                        print(f"[CLIENT] 文件 {filename} 下载成功")
                    else:
                        print(f"[CLIENT] 文件 {filename} 下载失败")
                else:
                    print(f"[CLIENT] 无效的OK响应格式: {response}")
            elif response.startswith(f"ERR {filename} NOT_FOUND"):
                print(f"[CLIENT] 服务器错误: 文件 {filename} 未找到")
            else:
                print(f"[CLIENT] 未知响应: {response}")


def main():
    import sys
    if len(sys.argv) != 4:
        print(f"用法: python3 {sys.argv[0]} <服务器主机> <服务器端口> <下载列表文件>")
        print("示例: python3 UDPclient.py localhost 51234 files.txt")
        sys.exit(1)

    server_host = sys.argv[1]
    server_port = int(sys.argv[2])
    download_list_file = sys.argv[3]

    client = UDPClient(server_host, server_port, download_list_file)
    client.process_download_list()


if __name__ == "__main__":
    main()