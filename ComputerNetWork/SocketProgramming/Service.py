# Constants for UDP header
class Constants:
    # UDP header
    UDP_HEADER_SIZE: int = 8
    UDP_SEGMENT_SIZE: int = 1024
    PAYLOAD_SIZE: int = UDP_SEGMENT_SIZE - UDP_HEADER_SIZE
    
    
