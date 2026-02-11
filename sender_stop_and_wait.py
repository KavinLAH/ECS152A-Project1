import socket
import time

UDP_PACKET_SIZE = 1024 # each udp packet is 1024 bytes total (header and payload)
SEQUENCE_ID_SIZE = 4 # sequence ID is 4 bytes
MESSAGE_SIZE = UDP_PACKET_SIZE - SEQUENCE_ID_SIZE
TIMEOUT = 0.5  # seconds - reduced for faster recovery
NUM_ITERATIONS = 1  # Runner script handles the 10 iterations
FILE_PATH = "project_1/2024_congestion_control_ecs152a/docker/file.mp3"
RECEIVER_HOST = "localhost"
RECEIVER_PORT = 5001


def create_packet(seq_id, data):
    # Create a packet with sequence ID and data
    # we knew we needed to convert the sequnce ID to bytes, so we used the LLM to help uswith that
    return int.to_bytes(seq_id, SEQUENCE_ID_SIZE, signed=True, byteorder='big') + data
    # each packet is strucutred like the [4 byte sequence id][up to 10 20 bytes payload]


def parse_ack(packet):
    # Parse an acknowledgement packet and return (ack_id, message)
    ack_id = int.from_bytes(packet[0:SEQUENCE_ID_SIZE], signed=True, byteorder='big')
    message = packet[SEQUENCE_ID_SIZE:].decode() # this ius decoding everything after the first four bytes to detect special messages like "fin" -> utlizied LLM to help us write this line (told us to use theb function)
    return ack_id, message


def send_file_stop_and_wait():
    # Send file using stop and wait protocol. Returns (throughput, avg_delay).
    # Read file data
    with open(FILE_PATH, 'rb') as f:
        file_data = f.read()
    
    total_bytes = len(file_data)
    packets = []
    
    # Creatijng all packets and utoiliziung a for loop to create the packets
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
        
        # Send each packet using stop and wait protocol
        for seq_id, data in packets:
            packet = create_packet(seq_id, data)
            packet_start_time = time.time()
            # Need to keep track of whether the sender received an ack or not
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
        
        # Need to keep track of whether the sender recevied a fin
        fin_received = False
        while not fin_received:
            udp_socket.sendto(empty_packet, (RECEIVER_HOST, RECEIVER_PORT))
            
            try:
                # Wait for ACK and FIN
                while True:
                    ack_packet, _ = udp_socket.recvfrom(PACKET_SIZE)
                    ack_id, message = parse_ack(ack_packet)
                    
                    # Check if it's a fin
                    if message == 'fin':
                        fin_received = True
                        break
            except socket.timeout:
                continue
        
        # Send FINACK
        finack_packet = create_packet(0, b'==FINACK==')
        udp_socket.sendto(finack_packet, (RECEIVER_HOST, RECEIVER_PORT))
        
        # Stop the timer now that we have received the finack
        end_time = time.time()
        
        # Calculate metrics as indicated in the professor's instruction
        total_time = end_time - start_time
        throughput = total_bytes / total_time  # bytes per second
        # if we have delays, then calculate the avg delay
        if delays:
            avg_delay = sum(delays) / len(delays)
        else:
            avg_delay = 0
        
        # return our final values
        return throughput, avg_delay


def main():
    # setting up the inital arrays to store our values
    throughputs = []
    delays = []
    metrics = []
    
    # running the sender_stop_and_wait function NUM_ITERATIONS times -> 10
    for _ in range(NUM_ITERATIONS):
        throughput, avg_delay = send_file_stop_and_wait()
        throughputs.append(throughput)
        delays.append(avg_delay)
        
        # Calculate performance metric using the formula given in the professor's instruction
        metric = 0
        if avg_delay > 0:
            metric = 0.3 * (throughput / 1000) + 0.7 / avg_delay
        metrics.append(metric)
    
    # Calculating the averages
    avg_throughput = sum(throughputs) / len(throughputs)
    avg_delay = sum(delays) / len(delays)
    avg_metric = sum(metrics) / len(metrics)
    
    # Output results
    print(f"{avg_throughput:.7f}")
    print(f"{avg_delay:.7f}")
    print(f"{avg_metric:.7f}")


if __name__ == "__main__":
    main()
