import os
import sys
import socket
import hashlib

TOTAL_PACKET_SIZE = 1024
SEQUENCE_NUM_SIZE = 4
CHECKSUM_SIZE = 32
HEADER_SIZE = SEQUENCE_NUM_SIZE + CHECKSUM_SIZE
PAYLOAD_SIZE = TOTAL_PACKET_SIZE - HEADER_SIZE
BYTE_ORDER = 'big'
TIMEOUT = 1  # seconds

class Client:
    def __init__(self, server_ip, server_port: int):
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.settimeout(TIMEOUT)

    def split_data(self, data: bytes):
        return [data[i:i + PAYLOAD_SIZE] for i in range(0, len(data), PAYLOAD_SIZE)]

    def send_data(self, data: bytes):
        segments = self.split_data(data)
        global sequence_number
        sequence_number = 0
        
        for segment in segments:
            while True:
                checksum = hashlib.sha256(segment).digest()
                header = sequence_number.to_bytes(SEQUENCE_NUM_SIZE, BYTE_ORDER) + checksum
                packet = header + segment
                self.client_socket.sendto(packet, (self.server_ip, self.server_port))

                try:
                    ack, _ = self.client_socket.recvfrom(SEQUENCE_NUM_SIZE)
                    ack_sequence_number = int.from_bytes(ack, BYTE_ORDER)

                    if ack_sequence_number == sequence_number:
                        print(f"Received ACK for segment {sequence_number}")
                        sequence_number += 1
                        print(f"Sending segment {sequence_number}")
                        break
                    else:
                        print(f"Incorrect ACK {ack_sequence_number} for segment {sequence_number}, resending...")
                except socket.timeout:
                    print(f"Timeout for segment {sequence_number}, resending...")
        

    def send_eof(self, sequence_number):
        eof_packet = sequence_number.to_bytes(SEQUENCE_NUM_SIZE, BYTE_ORDER) + hashlib.sha256(b'').digest() + b''
        while True:
            self.client_socket.sendto(eof_packet, (self.server_ip, self.server_port))
            try:
                ack, _ = self.client_socket.recvfrom(SEQUENCE_NUM_SIZE)
                ack_sequence_number = int.from_bytes(ack, BYTE_ORDER)
                if ack_sequence_number == sequence_number:
                    print("EOF sent and acknowledged.")
                    break
                else:
                    print("Incorrect ACK for EOF, resending...")
            except socket.timeout:
                print("Timeout for EOF, resending...")

    def send(self, file_path: str):
        file_name = os.path.basename(file_path).encode("utf-8")
        print(f"Sending file name: {file_name.decode('utf-8')}")
        self.send_data(file_name)

        with open(file_path, 'rb') as file:
            content = file.read()
            print(f"Sending file content ({len(content)} bytes).")
            self.send_data(content)
        
        print("Sending EOF.")
        self.send_eof(sequence_number)

        print("File sent successfully.")
        print(hashlib.sha256(open(file_path, 'rb').read()).hexdigest())
        self.client_socket.close()

def main():
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} <file_path> <server_ip> <server_port>")
        sys.exit(1)

    file_path = sys.argv[1]
    server_ip = sys.argv[2]
    server_port = int(sys.argv[3])

    client = Client(server_ip, server_port)
    client.send(file_path)

if __name__ == '__main__':
    main()
