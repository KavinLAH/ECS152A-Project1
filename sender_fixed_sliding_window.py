import socket
import time
import threading

# Constants
PACKET_SIZE = 1024
SEQ_ID_SIZE = 4
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE
TIMEOUT = 0.5  # seconds - reduced for faster recovery
WINDOW_SIZE = 100  # packets
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


def send_file_sliding_window():
    """Send file using fixed sliding window protocol. Returns (throughput, avg_delay)."""
    # Read file data
    with open(FILE_PATH, 'rb') as f:
        file_data = f.read()
    
    total_bytes = len(file_data)
    
    # Create all packets with their sequence IDs
    packets = {}
    seq_ids = []
    for i in range(0, total_bytes, MESSAGE_SIZE):
        seq_id = i
        data = file_data[i:i + MESSAGE_SIZE]
        packets[seq_id] = data
        seq_ids.append(seq_id)
    
    # Track packet send times for delay calculation
    packet_first_send_time = {}
    packet_ack_time = {}
    
    # Create UDP socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.settimeout(TIMEOUT)
        
        # Start timer for throughput
        start_time = time.time()
        
        # Window management
        window_base = 0  # Index in seq_ids
        next_to_send = 0  # Index in seq_ids
        
        while window_base < len(seq_ids):
            # Send packets within the window
            while next_to_send < len(seq_ids) and (next_to_send - window_base) < WINDOW_SIZE:
                seq_id = seq_ids[next_to_send]
                packet = create_packet(seq_id, packets[seq_id])
                udp_socket.sendto(packet, (RECEIVER_HOST, RECEIVER_PORT))
                
                # Record first send time
                if seq_id not in packet_first_send_time:
                    packet_first_send_time[seq_id] = time.time()
                
                next_to_send += 1
            
            # Receive multiple ACKs (drain the buffer)
            udp_socket.setblocking(False)
            received_any = False
            
            while True:
                try:
                    ack_packet, _ = udp_socket.recvfrom(PACKET_SIZE)
                    received_any = True
                    ack_id, _ = parse_ack(ack_packet)
                    ack_time = time.time()
                    
                    # Move window based on cumulative ACK
                    while window_base < len(seq_ids):
                        base_seq_id = seq_ids[window_base]
                        if base_seq_id < ack_id:
                            if base_seq_id not in packet_ack_time:
                                packet_ack_time[base_seq_id] = ack_time
                            window_base += 1
                        else:
                            break
                except BlockingIOError:
                    break
            
            udp_socket.setblocking(True)
            udp_socket.settimeout(TIMEOUT)
            
            # If no ACKs received, wait with timeout
            if not received_any:
                try:
                    ack_packet, _ = udp_socket.recvfrom(PACKET_SIZE)
                    ack_id, _ = parse_ack(ack_packet)
                    ack_time = time.time()
                    
                    while window_base < len(seq_ids):
                        base_seq_id = seq_ids[window_base]
                        if base_seq_id < ack_id:
                            if base_seq_id not in packet_ack_time:
                                packet_ack_time[base_seq_id] = ack_time
                            window_base += 1
                        else:
                            break
                except socket.timeout:
                    # On timeout, retransmit all packets in window
                    for i in range(window_base, min(next_to_send, len(seq_ids))):
                        seq_id = seq_ids[i]
                        packet = create_packet(seq_id, packets[seq_id])
                        udp_socket.sendto(packet, (RECEIVER_HOST, RECEIVER_PORT))
        
        # Send empty packet to signal end of transmission
        final_seq_id = total_bytes
        empty_packet = create_packet(final_seq_id, b'')
        
        fin_received = False
        while not fin_received:
            udp_socket.sendto(empty_packet, (RECEIVER_HOST, RECEIVER_PORT))
            
            try:
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
        
        # Calculate average delay
        delays = []
        for seq_id in packet_first_send_time:
            if seq_id in packet_ack_time:
                delay = packet_ack_time[seq_id] - packet_first_send_time[seq_id]
                delays.append(delay)
        
        avg_delay = sum(delays) / len(delays) if delays else 0
        
        return throughput, avg_delay


def main():
    throughputs = []
    delays = []
    metrics = []
    
    for _ in range(NUM_ITERATIONS):
        throughput, avg_delay = send_file_sliding_window()
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
