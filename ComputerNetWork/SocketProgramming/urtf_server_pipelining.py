import os
import sys
import socket
import hashlib
import time

TOTAL_PACKET_SIZE = 1450
SEQUENCE_NUM_SIZE = 4
CHECKSUM_SIZE = 32
HEADER_SIZE = SEQUENCE_NUM_SIZE + CHECKSUM_SIZE
PAYLOAD_SIZE = TOTAL_PACKET_SIZE - HEADER_SIZE
BYTE_ORDER = 'big'
TIMEOUT = 1  # seconds
WINDOW_SIZE = 10  # Size of the receiving window

class Server:
    def __init__(self, server_ip, server_port: int):
        self.server_ip = server_ip
        self.server_port = server_port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.bind((self.server_ip, self.server_port))
        self.buffer = {}  # Buffer to store out-of-order packets

    def receive(self):
        while True:
            try:
                # First, receive the file name
                filename_received = False
                expected_seq_num = 0
                file_name = None
                client_address = None
                
                while not filename_received:
                    data, client_address = self.server_socket.recvfrom(TOTAL_PACKET_SIZE)
                    
                    if len(data) < HEADER_SIZE:
                        print("Received incomplete packet, ignoring...")
                        continue
                    
                    # Extract header
                    header = data[:HEADER_SIZE]
                    sequence_number = int.from_bytes(header[:SEQUENCE_NUM_SIZE], BYTE_ORDER)
                    received_checksum = header[SEQUENCE_NUM_SIZE:]
                    
                    payload = data[HEADER_SIZE:]
                    calculated_checksum = hashlib.sha256(payload).digest()
                    
                    if received_checksum == calculated_checksum:
                        if sequence_number == 0:  # First packet contains filename
                            file_name = payload.decode("utf-8")
                            print(f"Receiving file name: {file_name}")
                            expected_seq_num = 0
                            filename_received = True
                            
                            # Send ACK for filename packet
                            self.server_socket.sendto((0).to_bytes(SEQUENCE_NUM_SIZE, BYTE_ORDER), client_address)
                        else:
                            print(f"Expected sequence 0 for filename, got {sequence_number}, sending ACK 0")
                            self.server_socket.sendto((0).to_bytes(SEQUENCE_NUM_SIZE, BYTE_ORDER), client_address)
                    else:
                        print("Checksum mismatch for filename packet, ignoring...")
                        
                
                # Now receive the file content with pipelining
                with open(file_name, 'wb') as file:
                    eof_received = False
                    
                    while not eof_received:
                        data, addr = self.server_socket.recvfrom(TOTAL_PACKET_SIZE)
                        
                        if len(data) < HEADER_SIZE:
                            print("Received an incomplete packet, ignoring...")
                            continue
                        
                        # Extract header
                        header = data[:HEADER_SIZE]
                        sequence_number = int.from_bytes(header[:SEQUENCE_NUM_SIZE], BYTE_ORDER)
                        received_checksum = header[SEQUENCE_NUM_SIZE:]
                        
                        payload = data[HEADER_SIZE:]
                        calculated_checksum = hashlib.sha256(payload).digest()
                            
                        
                        # Check if valid packet
                        if received_checksum == calculated_checksum:
                            # Check if it's EOF
                            if len(payload) == 0:
                                self.server_socket.sendto(sequence_number.to_bytes(SEQUENCE_NUM_SIZE, BYTE_ORDER), addr)
                                eof_received = True
                                continue
                            
                            # Store valid packets in buffer
                            if sequence_number >= expected_seq_num:
                                self.buffer[sequence_number] = payload
                            else:
                                print(f"Duplicate packet {sequence_number}, already processed")
                            
                            # Process in-order packets from buffer
                            while expected_seq_num in self.buffer:
                                file.write(self.buffer[expected_seq_num])
                                del self.buffer[expected_seq_num]
                                expected_seq_num += 1
                            
                            # Send cumulative ACK for highest in-order packet received
                            ack_num = expected_seq_num - 1
                            self.server_socket.sendto(ack_num.to_bytes(SEQUENCE_NUM_SIZE, BYTE_ORDER), addr)
                        else:
                            print(f"Checksum mismatch for segment {sequence_number}, ignoring...")
                            # Resend ACK for last correctly received packet
                            ack_num = expected_seq_num - 1
                            if ack_num >= 0:  # Only send ACK if at least one packet was received
                                self.server_socket.sendto(ack_num.to_bytes(SEQUENCE_NUM_SIZE, BYTE_ORDER), addr)
                                print(f"Resent ACK {ack_num} after checksum failure")
                
                print(f"File {file_name} received successfully.")
                print(hashlib.sha256(open(file_name, 'rb').read()).hexdigest())
                self.buffer.clear()  # Clear buffer for next file
                return 0

            except Exception as e:
                print(f"Error: {e}")
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