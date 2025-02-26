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

class Server:
    def __init__(self, server_ip, server_port: int):
        self.server_ip = server_ip
        self.server_port = server_port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.bind((self.server_ip, self.server_port))

    def receive(self):
        while True:
            try:
                # Receive file name
                data, client_address = self.server_socket.recvfrom(TOTAL_PACKET_SIZE)
                header = data[:HEADER_SIZE]
                file_name_payload = data[HEADER_SIZE:]
                file_name = file_name_payload.decode("utf-8")

                # Send ACK for file name
                self.server_socket.sendto((0).to_bytes(SEQUENCE_NUM_SIZE, BYTE_ORDER), client_address)
                print(f"Receiving file name: {file_name}")
                
                #detect EOF of file name
                if len(file_name_payload) == 0:
                    print("EOF received.")
                    continue

                with open(file_name, 'wb') as file:
                    expected_sequence_number = 0  # Start expecting the first data packet

                    while True:
                        data, client_address = self.server_socket.recvfrom(TOTAL_PACKET_SIZE)

                        if len(data) < HEADER_SIZE:
                            print("Received an incomplete packet, ignoring...")
                            continue

                        # Extract header
                        header = data[:HEADER_SIZE]
                        sequence_number = int.from_bytes(header[:SEQUENCE_NUM_SIZE], BYTE_ORDER)
                        received_checksum = header[SEQUENCE_NUM_SIZE:]

                        payload = data[HEADER_SIZE:]
                        calculated_checksum = hashlib.sha256(payload).digest()

                        # Valid packet check
                        if received_checksum == calculated_checksum:
                            if sequence_number == expected_sequence_number:
                                if len(payload) == 0:  # EOF check
                                    print("EOF received.")
                                    self.server_socket.sendto(sequence_number.to_bytes(SEQUENCE_NUM_SIZE, BYTE_ORDER), client_address)
                                    break
                                file.write(payload)
                                print(f"Received segment {sequence_number} ({len(payload)} bytes).")
                                expected_sequence_number += 1
                            else:
                                print(f"Out-of-order packet: expected {expected_sequence_number}, got {sequence_number}")
                        else:
                            print(f"Checksum mismatch for segment {sequence_number}, ignoring...")

                        # Send ACK
                        ack_header = (expected_sequence_number - 1).to_bytes(SEQUENCE_NUM_SIZE, BYTE_ORDER)
                        self.server_socket.sendto(ack_header, client_address)
                    
                
                print(f"File {file_name} received successfully.")
                print(hashlib.sha256(open(file_name, 'rb').read()).hexdigest())

            except socket.timeout:
                pass
            except KeyboardInterrupt:
                print("Server closed.")
                self.server_socket.close()
                break

def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <server_ip> <server_port>")
        sys.exit(1)

    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])
    server = Server(server_ip, server_port)

    print(f"Server is listening on {server_ip}:{server_port}")
    server.receive()

if __name__ == '__main__':
    main()
