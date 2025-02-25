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
TIMEOUT = 0.5 # seconds

class Client:
    def __init__(self, server_ip, server_port: int):
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.connect((self.server_ip, self.server_port))
        self.client_socket.settimeout(TIMEOUT)
        
    def split_data(self, data: bytes): 
        return [data[i:i + PAYLOAD_SIZE] for i in range(0, len(data), PAYLOAD_SIZE)]

    def send_data(self, data: bytes):
        segments = self.split_data(data)
        sequence_number = 0
        checksum = hashlib.sha256(data).digest()
        
        for segment in segments:
            
            if(sequence_number % 10 == 0):
                print(f"Sending segment {sequence_number} with size {len(segment)} bytes.")
            
            header = sequence_number.to_bytes(SEQUENCE_NUM_SIZE, BYTE_ORDER) + checksum
            packet = header + segment
            self.client_socket.sendto(packet, (self.server_ip, self.server_port))
            sequence_number += 1
            
        eof_marker = (b'\xff' * SEQUENCE_NUM_SIZE)
        self.client_socket.sendto(eof_marker, (self.server_ip, self.server_port))
        print("Sent EOF.")
        
    def send(self, file_path: str):
 
        # Send the file name
        file_name = os.path.basename(file_path).encode("utf-8")
        print(f"Sending file name: {file_name.decode('utf-8')}")
        self.send_data(file_name)
        
        # Send the file content
        with open(file_path, 'rb') as file:
            content = file.read()
            print(f"Sending file content of {len(content)} bytes.")
            self.send_data(content)
            
        print('File sent successfully.')
        self.client_socket.close()

def main():
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} <file_path> <server_ip> <server_port>")
        sys.exit(1)
        
    try:
        file_path = sys.argv[1]
        server_ip = sys.argv[2]
        server_port = int(sys.argv[3])
        
    except Exception:
        print(f"Usage: {sys.argv[0]} <file_path> <server_ip> <server_port>")
        sys.exit(1)

    client = Client(server_ip, server_port)
    client.send(file_path)
    
if __name__ == '__main__':
    main()
