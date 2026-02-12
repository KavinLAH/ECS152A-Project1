import socket
import time

UDP_PACKET_SIZE = 1024
SEQUENCE_ID_SIZE = 4
MESSAGE_SIZE = UDP_PACKET_SIZE - SEQUENCE_ID_SIZE
TIMEOUT = 0.5  # seconds - reduced for faster recovery
INITIAL_CWND = 1  # initial congestion window (packets)
INITIAL_SSTHRESH = 64  # initial slow start threshold (packets)
NUM_ITERATIONS = 10
FILE_PATH = "project_1/2024_congestion_control_ecs152a/docker/file.mp3"
RECEIVER_HOST = "localhost"
RECEIVER_PORT = 5001


def create_packet(seq_id, data):
    # Create a packet with sequence ID and data
    return int.to_bytes(seq_id, SEQUENCE_ID_SIZE, signed=True, byteorder='big') + data # Returning th packet, utilzied the LLM to help us use the int.to_bytes() function


def parse_ack(packet):
    # Parse an acknowledgement packet and return (ack_id, message)
    ack_id = int.from_bytes(packet[:SEQUENCE_ID_SIZE], signed=True, byteorder='big')
    message = packet[SEQUENCE_ID_SIZE:].decode() # utilized the LLM to help us use the decode function for the line 
    return ack_id, message


def send_file_tcp_reno():
    # Send file using TCP Reno protocol.
    # Returns (throughput, avg_delay)
    # Read file data
    with open(FILE_PATH, 'rb') as f:
        file_data = f.read()
    
    total_bytes = len(file_data)
    
    # Create all packets with their sequence IDs
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
    
    # Track packet send times for calculating delay
    packet_first_send_time = {}
    packet_ack_time = {}
    
    # Create a UDP socket to implement UDP sender as prof specified
    # utilzing the python socket library to establish a connection
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket: 
        udp_socket.settimeout(TIMEOUT)
        
        # Start timer for throughput so we can take that into account 
        start_time = time.time()
        
        # TCP Reno state -> Congestion control varibales we learned about in class 
        cwnd = INITIAL_CWND # this is intializing the congestion window size
        ssthresh = INITIAL_SSTHRESH # this is intializing the slow start threshold
        
        # Below are indices in the seq_ids list so it knows
        # which packet to send next and which packet to expect next
        window_base = 0
        next_to_send = 0 
        
        # This is going to keep track of the last ack we received
        # and the duplicate ack count
        last_ack = -1
        dup_ack_count = 0
        in_fast_recovery = False
        
        while window_base < len(seq_ids):
            # Calculate the window size
            effective_window = int(cwnd)
            
            # Send packets in the congestion window
            while next_to_send < len(seq_ids) and (next_to_send - window_base) < effective_window:
                seq_id = seq_ids[next_to_send]
                packet = create_packet(seq_id, packets[seq_id])
                udp_socket.sendto(packet, (RECEIVER_HOST, RECEIVER_PORT))
                
                # Record the first send time
                if seq_id not in packet_first_send_time:
                    packet_first_send_time[seq_id] = time.time()
                
                next_to_send += 1
            
            # Receive multiple ACKs -> we want to drain the buffer to prevent overflow
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
                
                    if ack_id > last_ack:
                        # New ACK received
                        
                        # Exit fast recovery if we were in it
                        if in_fast_recovery:
                            cwnd = ssthresh
                            in_fast_recovery = False
                        
                        # Update congestion window size based on slow start or congestion avoidance
                        if cwnd < ssthresh:
                            # Slow start is an exponential increase
                            cwnd += 1
                        else:
                            # Congestion avoidance is a linear increase
                            cwnd += 1.0 / cwnd
                        
                        # Move window based on the cumulative ACK
                        while window_base < len(seq_ids):
                            # Grab the sequence ID
                            base_seq_id = seq_ids[window_base]
                            # If the base sequence ID is less than the ACK ID
                            if base_seq_id < ack_id:
                                # Then we record its ACK time
                                if base_seq_id not in packet_ack_time:
                                    packet_ack_time[base_seq_id] = ack_time
                                window_base += 1
                            else:
                                break
                        # Update the last ACK
                        # Set duplicate ACK count back to 0
                        last_ack = ack_id
                        dup_ack_count = 0
                        
                    else:
                        # Duplicate ACK received oh no
                        dup_ack_count += 1
                        
                        # This means we have 3 duplicate ACKs and need to enter fast recovery
                        if dup_ack_count == 3 and not in_fast_recovery:
                            # Fast retransmit --> retransmit the lost packet
                            # Use formula as we learned in class
                            ssthresh = max(cwnd / 2, 2)
                            # increase the threshold by 3 and set to congestion window
                            cwnd = ssthresh + 3
                            in_fast_recovery = True
                            
                            # Retransmit the packet at the window
                            if window_base < len(seq_ids):
                                seq_id = seq_ids[window_base]
                                packet = create_packet(seq_id, packets[seq_id])
                                udp_socket.sendto(packet, (RECEIVER_HOST, RECEIVER_PORT))
                        
                        elif in_fast_recovery:
                            # Fast recovery --> retransmit immediately after missing
                            cwnd += 1
                        
                except BlockingIOError:
                    # No more ACKs in buffer so we can break
                    break
            
            udp_socket.setblocking(True)
            udp_socket.settimeout(TIMEOUT)
            
            # If we didn't receive any ACKs wait with a timeout
            if not received_any:
                try:
                    ack_packet, _ = udp_socket.recvfrom(UDP_PACKET_SIZE)
                    ack_id, _ = parse_ack(ack_packet)
                    ack_time = time.time()
                    
                    # if the ACK ID is greater than the last ACK
                    if ack_id > last_ack:
                        # If we are in fast recovery, then set congestion window to threshold
                        # Then exit it
                        if in_fast_recovery:
                            cwnd = ssthresh
                            in_fast_recovery = False
                        # If we have congestion window less than threshold, then we can increase it by 1 until it equals threshold
                        if cwnd < ssthresh:
                            cwnd += 1
                        # Otherwise we can increase it by 1/cwnd
                        else:
                            cwnd += 1.0 / cwnd
                        # While our window size is less than number of seq IDs
                        while window_base < len(seq_ids):
                            # Grab the sequence ID
                            base_seq_id = seq_ids[window_base]
                            # If the base sequence ID is less than the ACK ID
                            # Then we record its ACK time
                            # And move the window base forward
                            if base_seq_id < ack_id:
                                if base_seq_id not in packet_ack_time:
                                    packet_ack_time[base_seq_id] = ack_time
                                window_base += 1
                            else:
                                break
                        # Set last ack to last one
                        # Then set duplicate ACK count back to 0
                        last_ack = ack_id
                        dup_ack_count = 0
                    else:
                        # Then if we received a duplicate ACK, increase by 1
                        dup_ack_count += 1
                        # Now if we have 3 duplicates and we are not in fast recovery
                        if dup_ack_count == 3 and not in_fast_recovery:
                            # Follow formula in class
                            ssthresh = max(cwnd / 2, 2)
                            cwnd = ssthresh + 3
                            # Enter fast recovery
                            in_fast_recovery = True
                            # Retransmit the lost packet
                            # Use formula as we learned in class
                            if window_base < len(seq_ids):
                                seq_id = seq_ids[window_base]
                                packet = create_packet(seq_id, packets[seq_id])
                                udp_socket.sendto(packet, (RECEIVER_HOST, RECEIVER_PORT))
                        elif in_fast_recovery:
                            # If in fast recovery retransmit immediately
                            # Increase congestion window by 1
                            cwnd += 1
                            
                except socket.timeout:
                    # Timeout --> go back to slow start
                    # Apply formulas in class
                    ssthresh = max(cwnd / 2, 2)
                    cwnd = 1
                    in_fast_recovery = False
                    dup_ack_count = 0
                    
                    # Retransmit all packets in window
                    for i in range(window_base, min(next_to_send, len(seq_ids))):
                        seq_id = seq_ids[i]
                        packet = create_packet(seq_id, packets[seq_id])
                        udp_socket.sendto(packet, (RECEIVER_HOST, RECEIVER_PORT))
        
        # Send empty packet to signal the end of transmission
        final_seq_id = total_bytes
        empty_packet = create_packet(final_seq_id, b'')
        
        # Wait for a FIN from receiver
        fin_received = False
        # Keep sending empty packet to receiver until we receive a FIN
        while not fin_received:
            udp_socket.sendto(empty_packet, (RECEIVER_HOST, RECEIVER_PORT))
            
            try:
                while True:
                    ack_packet, _ = udp_socket.recvfrom(UDP_PACKET_SIZE)
                    ack_id, message = parse_ack(ack_packet)
                    
                    if message == 'fin':
                        fin_received = True
                        break
            except socket.timeout:
                continue
        
        # Send FINACK now after receiving FIN from receiver
        finack_packet = create_packet(0, b'==FINACK==')
        udp_socket.sendto(finack_packet, (RECEIVER_HOST, RECEIVER_PORT))
        
        # Stop the timer as we're done
        end_time = time.time()
        
        # Calculate the metrics as indicated in instructions
        total_time = end_time - start_time
        throughput = total_bytes / total_time  # bytes per second
        
        # Calculate the average delay across 10 iterations (same as all other files)
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
        throughput, avg_delay = send_file_tcp_reno()
        throughputs.append(throughput)
        delays.append(avg_delay)
        
        # Calculate performance metric (same as all other files)
        metric = 0.3 * (throughput / 1000) + 0.7 / avg_delay if avg_delay > 0 else 0
        metrics.append(metric)
    
    # Calculate averages (same as all other files)
    avg_throughput = sum(throughputs) / len(throughputs)
    avg_delay = sum(delays) / len(delays)
    avg_metric = sum(metrics) / len(metrics)
    
    # Output results
    print(f"{avg_throughput:.7f}")
    print(f"{avg_delay:.7f}")
    print(f"{avg_metric:.7f}")


if __name__ == "__main__":
    main()
