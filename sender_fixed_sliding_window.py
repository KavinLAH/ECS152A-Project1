import socket
import time
import threading

# Constants
UDP_PACKET_SIZE = 1024
SEQUENCE_ID_SIZE = 4
MESSAGE_SIZE = UDP_PACKET_SIZE - SEQUENCE_ID_SIZE
TIMEOUT = 0.5  # seconds - reduced for faster recovery
WINDOW_SIZE = 100  # packets
NUM_ITERATIONS = 10 # ten iterations per professors request
FILE_PATH = "project_1/2024_congestion_control_ecs152a/docker/file.mp3"
RECEIVER_HOST = "localhost" # connection to localhost
RECEIVER_PORT = 5001 # Docker container port that prof set up


def create_packet(seq_id, data):
    # Create a packet with sequence ID and data
    return int.to_bytes(seq_id, SEQUENCE_ID_SIZE, signed=True, byteorder='big') + data


def parse_ack(packet):
    # Parse an acknowledgement packet and return (ack_id, message)
    ack_id = int.from_bytes(packet[:SEQUENCE_ID_SIZE], signed=True, byteorder='big')
    message = packet[SEQUENCE_ID_SIZE:].decode()
    return ack_id, message


def send_file_sliding_window():
    # Send file using fixed sliding window protocol. Returns (throughput, avg_delay).
    # Read file data
    with open(FILE_PATH, 'rb') as f:
        file_data = f.read()
    
    total_bytes = len(file_data)
    
    # Create all packets with their sequence IDs
    # Dictionary to store packets with their sequence ID and payload
    packets = {}
    seq_ids = []
    # Loop through whole message
    # Create packets with its their sequence ID and payload
    # And add to the above list and dict each time
    for i in range(0, total_bytes, MESSAGE_SIZE):
        seq_id = i
        data = file_data[i:i + MESSAGE_SIZE]
        packets[seq_id] = data
        seq_ids.append(seq_id)
    
    # Track packet send times for delay calculation
    packet_first_send_time = {}
    packet_ack_time = {}
    
    # Create a UDP socket to implement UDP sender as prof specified
    # utilzing the python socket library to establish a connection
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.settimeout(TIMEOUT)
        
        # Start timer for throughput
        start_time = time.time()
        
        # Below are indices in the seq_ids list so it knows
        # which packet to send next and which packet to expect next
        window_base = 0
        next_to_send = 0  
        
        # Loop to send all packets within the specified window
        while window_base < len(seq_ids):
            # Send all packets within the specified window while you're in it
            while next_to_send < len(seq_ids) and (next_to_send - window_base) < WINDOW_SIZE:
                seq_id = seq_ids[next_to_send]
                packet = create_packet(seq_id, packets[seq_id])
                udp_socket.sendto(packet, (RECEIVER_HOST, RECEIVER_PORT))
                
                # Record first send time for delay calculation
                if seq_id not in packet_first_send_time:
                    packet_first_send_time[seq_id] = time.time()
                
                # Move to the next packet to send
                next_to_send += 1
            
            # Receive multiple ACKs (drain the buffer)
            udp_socket.setblocking(False)
            received_any = False
            
            # Loop to receive multiple ACKs
            while True:
                # Try to receive an ACK
                try:
                    # Receive an ACK
                    # If no ACK is received then we end the loop
                    ack_packet, _ = udp_socket.recvfrom(UDP_PACKET_SIZE)
                    received_any = True
                    ack_id, _ = parse_ack(ack_packet)
                    ack_time = time.time()
                    
                    # Move window based on cumulative ACK
                    while window_base < len(seq_ids):
                        base_seq_id = seq_ids[window_base]
                        # Move window pointer to the next packet to send
                        if base_seq_id < ack_id:
                            # Record ACK time for delay calculation
                            if base_seq_id not in packet_ack_time:
                                packet_ack_time[base_seq_id] = ack_time
                            window_base += 1
                        else:
                            break
                except BlockingIOError:
                    break
            
            udp_socket.setblocking(True)
            udp_socket.settimeout(TIMEOUT)
            
            # If no ACKs are received wait with a timeout
            if not received_any:
                try:
                    # Receive an ACK
                    # If no ACK is received then we end the loop
                    ack_packet, _ = udp_socket.recvfrom(UDP_PACKET_SIZE)
                    ack_id, _ = parse_ack(ack_packet)
                    ack_time = time.time()
                    
                    # Move the window based on the cumulative ACK
                    while window_base < len(seq_ids):
                        # Move window pointer to the next packet to send
                        base_seq_id = seq_ids[window_base]
                        if base_seq_id < ack_id:
                            if base_seq_id not in packet_ack_time:
                                packet_ack_time[base_seq_id] = ack_time
                            window_base += 1
                        else:
                            break
                except socket.timeout:
                    # During a timeout retransmit all of the packets in the window
                    for i in range(window_base, min(next_to_send, len(seq_ids))):
                        seq_id = seq_ids[i]
                        packet = create_packet(seq_id, packets[seq_id])
                        udp_socket.sendto(packet, (RECEIVER_HOST, RECEIVER_PORT))
        
        # Send an empty packet to signal end of transmitting packets
        final_seq_id = total_bytes
        empty_packet = create_packet(final_seq_id, b'')
        
        # Now we wait for our sender to receive a FIN to terminate connection
        fin_received = False
        # While we have not received a FIN keep sending empty packets
        while not fin_received:
            udp_socket.sendto(empty_packet, (RECEIVER_HOST, RECEIVER_PORT))
            
            # try to receive an ACK
            try:
                while True:
                    ack_packet, _ = udp_socket.recvfrom(UDP_PACKET_SIZE)
                    ack_id, message = parse_ack(ack_packet)
                    
                    if message == 'fin':
                        fin_received = True
                        break
            except socket.timeout:
                continue
        
        # Send FINACK to respond to the FIN by receiver
        finack_packet = create_packet(0, b'==FINACK==')
        udp_socket.sendto(finack_packet, (RECEIVER_HOST, RECEIVER_PORT))
        
        # Stop the timer now that it's done
        end_time = time.time()
        
        # Calculate metrics as specified by professor
        total_time = end_time - start_time
        throughput = total_bytes / total_time  # bytes per second
        
        # Calculate average delay over all 10 iterations
        delays = []
        for seq_id in packet_first_send_time:
            if seq_id in packet_ack_time:
                delay = packet_ack_time[seq_id] - packet_first_send_time[seq_id]
                delays.append(delay)
        
        if delays:
            avg_delay = sum(delays) / len(delays)
        else:
            avg_delay = 0
        
        return throughput, avg_delay


def main():
    throughputs = []
    delays = []
    metrics = []
    
    # Run 10 iterations
    for _ in range(NUM_ITERATIONS):
        throughput, avg_delay = send_file_sliding_window()
        throughputs.append(throughput)
        delays.append(avg_delay)
        
        # Calculate performance metrics
        # Follow the formula specified by professor
        metric = 0.3 * (throughput / 1000) + 0.7 / avg_delay if avg_delay > 0 else 0
        metrics.append(metric)
    
    # Calculate all averages
    avg_throughput = sum(throughputs) / len(throughputs)
    avg_delay = sum(delays) / len(delays)
    avg_metric = sum(metrics) / len(metrics)
    
    # Output results
    print(f"{avg_throughput:.7f}")
    print(f"{avg_delay:.7f}")
    print(f"{avg_metric:.7f}")


if __name__ == "__main__":
    main()
