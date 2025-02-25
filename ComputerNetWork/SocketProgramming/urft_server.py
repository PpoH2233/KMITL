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

class Server:
    def __init__(self, server_ip, server_port: int):
        self.server_ip = server_ip
        self.server_port = server_port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # DGRAM is for UDP
        self.server_socket.bind((self.server_ip, self.server_port))
        self.server_socket.settimeout(TIMEOUT)
                        
    
    def receive(self):
        while True:
            try:
                """
                Step
                1: Receive the file name / create a new file
                2: Receive the file content 
                3: Save the file
                """
                
                # Receive the file name
                data, _ = self.server_socket.recvfrom(TOTAL_PACKET_SIZE)
                header = data[:HEADER_SIZE]
                file_name_payload = data[HEADER_SIZE:]
                file_name = file_name_payload.decode("utf-8")


                with open(file_name, 'wb') as file:
                    print(f"Receiving file name: {file_name}")
                    
                    
                    # Receive the file content
                    segment_number = 0
                    while True:
                        data, _ = self.server_socket.recvfrom(TOTAL_PACKET_SIZE)
                        
                        # Extract the header from the received data
                        header = data[:HEADER_SIZE]
                 
                        received_checksum = header[SEQUENCE_NUM_SIZE:]
                        
                        
                        # if len(data) == SEQUENCE_NUM_SIZE and data == (b'\xff' * SEQUENCE_NUM_SIZE):                            
                        #     print("EOF received.")
                        #     break
                        
                        payload = data[HEADER_SIZE:]
                        
                        # Calculate checksum of the received payload
                        calculated_checksum = hashlib.sha256(payload).digest()
                        
                        if received_checksum != calculated_checksum:
                            print(f"Checksum error in segment {segment_number}.")
                            continue
                        
                        print(payload)
                        file.write(payload)

                        segment_number += 1
                        print(f"Receiving segment {segment_number} with size {len(data)} bytes.")
                    
                # check sum of the file
                with open(file_name, 'rb') as file:
                    content = file.read()
                    checksum = hashlib.sha256(content).digest()
                    
                    if(received_checksum != checksum):
                        print("Checksum error.")
                        os.remove(file_name)
                        continue
                    
                    print(f"Checksum of the file: {checksum}")
                    
                print(f"File {file_name} received successfully.")                
                
                
            except socket.timeout:
                # print("Timeout...")
                pass
            
            except KeyboardInterrupt:
                print("Server closed.")
                self.server_socket.close()
                break    
                   

def main():
    try:
        if len(sys.argv) < 3:
            print(f"Usage: {sys.argv[0]} <server_ip> <server_port>")
            sys.exit(1)
            
        server_ip = sys.argv[1]
        server_port = int(sys.argv[2])
        server = Server(server_ip, server_port)
        
        print(f"Server is listening on {server_ip}:{server_port}")
        server.receive()
        
    except Exception:
        print(f"""Usage: {sys.argv[0]} <server_ip> <server_port>""")
        sys.exit(1)
    

if __name__ == '__main__':
    main()