# ECS 152A Project 2 Report - Congestion Control

**Team Members:**
- Name 1: Kavin Agarwal (Student ID: 922172498)
- Name 2: Raquib Alam (Student ID: 922032910)

---

## 1. Stop-and-Wait Protocol

### Technical Explanation

The Stop-and-Wait protocol is a simple form sending data reliably using UDP. But, it's not the most efficient approach to send packets as the sender always has to wait for an ACK for every packet before sending the next one, which is why it took our code 30-40 minutes to run (so long!). Our implementation follows this logic we mapped together:

**Packet Structure**: Each packet has a 4-byte sequence ID followed by up to 1020 bytes of data. The sequence ID represents the byte offset in the original file, enabling the receiver to form the data accurately and in order.

**Transmission Logic**: The sender reads the file.mp3 and divides it into 1020-byte chunks. For each packet, the sender does the following:
1. Creates the packet with the sequence ID and data
2. Records the send timestamp for delay calculation
3. Transmits the packet to the receiver at localhost:5001
4. Waits for an ACK with a 1 second timeout

**Handling the ACKs**: When an ACK arrives, the sender checks if the current acknowledged sequence ID is higher than the current packet's sequence ID. If that is the case, the packet is considered delivered by the sender. If a timeout occurs, the sender will then resend the packet.

**Ending the connection between sender/receiver**: After the sender has received an ACK for all sent packets, the sender will finally send an empty packet (with the sequence ID = total file size) to initiate the ending of the connection. It then waits for the receiver to send a FIN packet. Once it receives it, then it responds back with a FINACK packet to terminate the connection with the receiver.

**Metrics Collection**: Throughput is calculated as the total_bytes / total_time, representing the total data sent over an amount of time. Per-packet delay is measured from the first send attempt to final ACK receipt, effectively the difference between when it was sent by the sender and received by the receiver. The performance metric combines both: 0.3 * (throughput/1000) + 0.7 / avg_delay.

**External Sources**: Neso Academy, Lecture #3, Used ChatGPT to guide our understanding of these topics as well and refine our ideas.

### Results

| Metric | Average | Standard Deviation |
|--------|---------|-------------------|
| Throughput (bytes/sec) | 6714.9189371 | 85.4464623 |
| Avg Packet Delay (sec) | 0.1518628 | 0.0019288 |
| Performance Metric | 6.6238988 | 0.0843042 |

**Output Screenshot**:

![Stop-and-Wait Output](stop_and_wait_screenshot.png)

---

## 2. Fixed Sliding Window Protocol

### Technical Explanation

The Fixed Sliding Window protocol significantly improves our throughput over Stop-and-Wait by allowing multiple packets in flight all the same time instead of waiting for an ACK for each individual packet. Our implementation uses a window size of 100 packets.

**Window Management**: We use two pointers: `window_base` (the oldest unacknowledged packet) and `next_to_send` (the next packet to send). Packets are sent as long as (next_to_send - window_base) < WINDOW_SIZE and data remains. In short, the sender sends packets when we are in the window and have data to send.

**Cumulative ACKs**: The receiver sends cumulative acknowledgments indicating the next expected byte offset. When an ACK is received, the sender slides the window forward by incrementing the window_base to match the ACK. This efficiently handles out-of-order delivery as multiple packets can be acknowledged with a single ACK.

**Packet Loss Handling**: On a socket timeout (1 second), we retransmit all unacknowledged packets currently in the window (Go-Back-N behavior). This ensures reliability even with the network profile's variable packet loss rate (0-20%).

### Window Adjustment Technique

Unlike TCP Reno, the Fixed Sliding Window maintains a constant window size of 100 packets regardless of network conditions. The window advances only when the cumulative ACKs arrive:

1. If ACK_id > seq_id of packet at window_base: slide window forward
2. Track all packets between old and new window_base as acknowledged
3. Send new packets to fill the window up to WINDOW_SIZE

This simplicity makes it easier to implement but it's less adaptive than TCP's dynamic congestion control as it keeps a fixed window size.

**Delay Tracking**: We record the first send time for each packet and the time when its ACK is received, effectively calculating the delay from the first send attempt to final ACK receipt. For retransmitted packets, the delay is measured from the original send time, as specified in the assignment.

**External Sources**: Neso Academy, Lecture #3, Used ChatGPT to explain Fixed Sliding Window in a more simple manner.

### Results

| Metric | Average | Standard Deviation |
|--------|---------|-------------------|
| Throughput (bytes/sec) | 90895.7855390 | 6146.9697444 |
| Avg Packet Delay (sec) | 1.1101397 | 0.0650894 |
| Performance Metric | 27.8992869 | 1.8830586 |

**Output Screenshot**:

![Fixed Sliding Window Output](sliding_window_screenshot.png)

---

## 3. TCP Reno (Extra Credit)

### Technical Explanation

TCP Reno uses adaptive congestion control with slow start, congestion avoidance, and fast recovery mechanisms.

**Slow Start Threshold**: The initial slow start threshold (ssthresh) is set to 64 packets. When the congestion window (cwnd) is less than ssthresh, the sender is in the slow start phase. That is when the sender doubles the congestion window each round trip time (RTT). This is implemented by incrementing cwnd by 1 for each ACK.

**AIMD Implementation**: 
- **Additive Increase**: In congestion avoidance (cwnd >= ssthresh), cwnd increases by 1/cwnd for each ACK, resulting in approximately one packet increase per RTT.
- **Multiplicative Decrease**: On every timeout, ssthresh = cwnd/2 and cwnd = 1 (back to the slow start phase).

**Fast Retransmit and Fast Recovery**:
1. Keep track of all duplicate ACKs (ACKs with the same sequence number as the last)
2. On 3 duplicate ACKs: we set ssthresh to cwnd/2, then set the cwnd to ssthresh + 3. Finally the sender retransmits the lost packet.
3. During the fast recovery phase, each additional duplicate ACK increases cwnd by 1, leading to linear growth.
4. Upon the sender receiving a new ACK, it exits the fast recovery phase and it sets cwnd = ssthresh.

### Handling Congestion

Example scenario:
- cwnd grows from 1 to 2 to 4 to 8 to ... to 64 (slow start)
- At cwnd = 64 (ssthresh), switch from slow start to congestion avoidance.
- cwnd grows linearly: 64 to 65 to 66 to ...
- On 3 dup ACKs at cwnd = 80: set the ssthresh to 40 and cwnd to 40 + 3 = 43 and retransmit the lost packet.
- New ACK arrives: Half the cwnd to 40 and it grows linearly.

**External Sources**: Lecture #4, Used ChatGPT to help me explain all phases and how to transition between.

### Results

| Metric | Average | Standard Deviation |
|--------|---------|-------------------|
| Throughput (bytes/sec) | 90469.3276998 | 4563.9935462 |
| Avg Packet Delay (sec) | 0.5977813 | 0.1550600 |
| Performance Metric | 28.3965228 | 1.3128171 |

**Output Screenshot**:

![TCP Reno Output](tcp_reno_screenshot.png)

---

## Submission Certification

I certify that all submitted work is my own work. I have completed all of the assignments on my own without assistance from others except as indicated by appropriate citation. I have read and understand the university policy on plagiarism and academic dishonesty.

**Team Member 1 Contributions**: Worked on the TCP Reno part of report and the algorithm. Collaborated with Raq on the code for Sliding Window and Stop and Wait.

| Kavin Agarwal| KA | 2/12/2026 |
|-----------|-----------|------|
| | | |

**Team Member 2 Contributions**: Worked on the Stop and Wait and Sliding Window part of the report and the algorithm. Collaborated with Kavin on the code for TCP Reno.

| Raquib Alam | RA | 2/12/2026 |
|-----------|-----------|------|
| | | |
