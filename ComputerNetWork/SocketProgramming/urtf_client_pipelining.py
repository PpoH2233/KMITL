import os
import sys
import socket
import hashlib
import time
from collections import deque

TOTAL_PACKET_SIZE = 1450
SEQUENCE_NUM_SIZE = 4
CHECKSUM_SIZE = 32
HEADER_SIZE = SEQUENCE_NUM_SIZE + CHECKSUM_SIZE
PAYLOAD_SIZE = TOTAL_PACKET_SIZE - HEADER_SIZE
BYTE_ORDER = 'big'
TIMEOUT = 1  # seconds
WINDOW_SIZE = 10  # Number of packets that can be in-flight at once

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
        base = 0  # First unacknowledged packet
        next_seq_num = 0  # Next packet to send
        
        window = {}  # Map of sequence number to (packet, last_sent_time, original_segment)
        
        while base < len(segments):
            # Send packets within the window
            if next_seq_num % 10 == 0:
                print(f"Sending segments from {next_seq_num} to {min(base + WINDOW_SIZE, len(segments)) - 1}")
            
            while next_seq_num < len(segments) and next_seq_num < base + WINDOW_SIZE:
                segment = segments[next_seq_num]
                checksum = hashlib.sha256(segment).digest()
                header = next_seq_num.to_bytes(SEQUENCE_NUM_SIZE, BYTE_ORDER) + checksum
                packet = header + segment
                     
                self.client_socket.sendto(packet, (self.server_ip, self.server_port))
                # Store the original segment to enable correct retransmission
                window[next_seq_num] = (packet, time.time(), segment)

                next_seq_num += 1
            
            # Try to receive ACKs
            try:
                ack, _ = self.client_socket.recvfrom(SEQUENCE_NUM_SIZE)
                ack_sequence_number = int.from_bytes(ack, BYTE_ORDER)
                
                print(f"Received ACK for segment {ack_sequence_number}")
                
                # Handle ACK and update the window
                if ack_sequence_number >= base:
                    # Cumulative ACK - acknowledge all packets up to ack_sequence_number
                    for seq_num in list(window.keys()):
                        if seq_num <= ack_sequence_number:
                            del window[seq_num]
                    base = ack_sequence_number + 1
                elif ack_sequence_number < base:
                    
                    if base - ack_sequence_number > 1:  # More than one packet gap

                        # Reset next_seq_num to retransmit from the ACK+1 position
                        potential_rollback = ack_sequence_number + 1
                        if potential_rollback < next_seq_num:
                            # Only roll back if it's less than our current position
                            next_seq_num = potential_rollback
                            
                            # We should regenerate packets for numbers that might be missing from window
                            for seq_to_fix in range(potential_rollback, min(base + WINDOW_SIZE, len(segments))):
                                if seq_to_fix not in window:
                                    # Regenerate the packet properly with correct checksum
                                    segment = segments[seq_to_fix]
                                    checksum = hashlib.sha256(segment).digest()
                                    header = seq_to_fix.to_bytes(SEQUENCE_NUM_SIZE, BYTE_ORDER) + checksum
                                    packet = header + segment
                                    window[seq_to_fix] = (packet, time.time(), segment)
                  
                
            except socket.timeout:
                # Timeout occurred, check if we need to resend any packets
                current_time = time.time()
                for seq_num, (packet, last_sent_time, original_segment) in list(window.items()):
                    if current_time - last_sent_time > TIMEOUT:
                   
                        # Regenerate the packet with correct headers to avoid propagating corrupted packets
                        checksum = hashlib.sha256(original_segment).digest()
                        header = seq_num.to_bytes(SEQUENCE_NUM_SIZE, BYTE_ORDER) + checksum
                        fresh_packet = header + original_segment
                        
                        self.client_socket.sendto(fresh_packet, (self.server_ip, self.server_port))
                        window[seq_num] = (fresh_packet, current_time, original_segment)
            
            
        
        return next_seq_num  # Return last sequence number for EOF

    def send_eof(self, sequence_number):
        eof_packet = sequence_number.to_bytes(SEQUENCE_NUM_SIZE, BYTE_ORDER) + hashlib.sha256(b'').digest() + b''
        retry_count = 0
        max_retries = 5
        
        while retry_count < max_retries:
            self.client_socket.sendto(eof_packet, (self.server_ip, self.server_port))
            try:
                ack, _ = self.client_socket.recvfrom(SEQUENCE_NUM_SIZE)
                ack_sequence_number = int.from_bytes(ack, BYTE_ORDER)
                if ack_sequence_number == sequence_number:
                    print("EOF sent and acknowledged.")
                    return True
                else:
                    print("Incorrect ACK for EOF, resending...")
            except socket.timeout:
                print("Timeout for EOF, resending...")
            
            retry_count += 1
        
        print("Failed to confirm EOF after maximum retries")
        return False

    def send(self, file_path: str):
        file_name = os.path.basename(file_path).encode("utf-8")
        print(f"Sending file name: {file_name.decode('utf-8')}")
        last_seq = self.send_data(file_name)

        start_time = time.time()
        
        with open(file_path, 'rb') as file:
            content = file.read()
            print(f"Sending file content ({len(content)} bytes).")
            last_seq = self.send_data(content)
        
        print("Sending EOF.")
        
        
        if self.send_eof(last_seq):
            print("File sent successfully.")
            print(hashlib.sha256(open(file_path, 'rb').read()).hexdigest())
        else:
            print("File transmission may not have completed successfully.")
            
        elapsed = time.time() - start_time
        print(f"Total time taken: {elapsed:.2f} seconds")
        
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
    
    return 0

if __name__ == '__main__':
    main()