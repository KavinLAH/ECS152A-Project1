import socket
import time

# Constants
PACKET_SIZE = 1024
SEQ_ID_SIZE = 4
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE
TIMEOUT = 0.5  # seconds - reduced for faster recovery
NUM_ITERATIONS = 1  # Runner script handles the 10 iterations
FILE_PATH = "project_1/2024_congestion_control_ecs152a/docker/file.mp3"
RECEIVER_HOST = "localhost"
RECEIVER_PORT = 5001


def create_packet(seq_id, data):
    """Create a packet with sequence ID and data."""
    return int.to_bytes(seq_id, SEQ_ID_SIZE, signed=True, byteorder='big') + data


def parse_ack(packet):
    """Parse an acknowledgement packet and return (ack_id, message)."""
    ack_id = int.from_bytes(packet[:SEQ_ID_SIZE], signed=True, byteorder='big')
    message = packet[SEQ_ID_SIZE:].decode()
    return ack_id, message


def send_file_stop_and_wait():
    """Send file using stop-and-wait protocol. Returns (throughput, avg_delay)."""
    # Read file data
    with open(FILE_PATH, 'rb') as f:
        file_data = f.read()
    
    total_bytes = len(file_data)
    packets = []
    
    # Create all packets
    for i in range(0, total_bytes, MESSAGE_SIZE):
        seq_id = i
        data = file_data[i:i + MESSAGE_SIZE]
        packets.append((seq_id, data))
    
    # Create UDP socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.settimeout(TIMEOUT)
        
        # Start timer for throughput
        start_time = time.time()
        
        delays = []
        
        # Send each packet using stop-and-wait
        for seq_id, data in packets:
            packet = create_packet(seq_id, data)
            packet_start_time = time.time()
            acked = False
            
            while not acked:
                # Send packet
                udp_socket.sendto(packet, (RECEIVER_HOST, RECEIVER_PORT))
                
                try:
                    # Wait for ACK
                    ack_packet, _ = udp_socket.recvfrom(PACKET_SIZE)
                    ack_id, _ = parse_ack(ack_packet)
                    
                    # Check if this is the ACK we're waiting for
                    if ack_id > seq_id:
                        acked = True
                        delay = time.time() - packet_start_time
                        delays.append(delay)
                except socket.timeout:
                    # Retransmit on timeout
                    continue
        
        # Send empty packet to signal end of transmission
        final_seq_id = total_bytes
        empty_packet = create_packet(final_seq_id, b'')
        
        fin_received = False
        while not fin_received:
            udp_socket.sendto(empty_packet, (RECEIVER_HOST, RECEIVER_PORT))
            
            try:
                # Wait for ACK and FIN
                while True:
                    ack_packet, _ = udp_socket.recvfrom(PACKET_SIZE)
                    ack_id, message = parse_ack(ack_packet)
                    
                    if message == 'fin':
                        fin_received = True
                        break
            except socket.timeout:
                continue
        
        # Send FINACK
        finack_packet = create_packet(0, b'==FINACK==')
        udp_socket.sendto(finack_packet, (RECEIVER_HOST, RECEIVER_PORT))
        
        # Stop timer
        end_time = time.time()
        
        # Calculate metrics
        total_time = end_time - start_time
        throughput = total_bytes / total_time  # bytes per second
        avg_delay = sum(delays) / len(delays) if delays else 0
        
        return throughput, avg_delay


def main():
    throughputs = []
    delays = []
    metrics = []
    
    for _ in range(NUM_ITERATIONS):
        throughput, avg_delay = send_file_stop_and_wait()
        throughputs.append(throughput)
        delays.append(avg_delay)
        
        # Calculate performance metric
        metric = 0.3 * (throughput / 1000) + 0.7 / avg_delay if avg_delay > 0 else 0
        metrics.append(metric)
    
    # Calculate averages
    avg_throughput = sum(throughputs) / len(throughputs)
    avg_delay = sum(delays) / len(delays)
    avg_metric = sum(metrics) / len(metrics)
    
    # Output results (3 lines, 7 decimal places)
    print(f"{avg_throughput:.7f}")
    print(f"{avg_delay:.7f}")
    print(f"{avg_metric:.7f}")


if __name__ == "__main__":
    main()
