# ECS 152A Project 2 Report - Congestion Control

**Team Members:**
- Name 1: _________________ (Student ID: _______________)
- Name 2: _________________ (Student ID: _______________)

---

## 1. Stop-and-Wait Protocol

### Technical Explanation

The Stop-and-Wait protocol is the simplest form of reliable data transfer over UDP. Our implementation follows these key steps:

**Packet Structure**: Each packet consists of a 4-byte sequence ID (big-endian, signed integer) followed by up to 1020 bytes of data. The sequence ID represents the byte offset in the original file, enabling the receiver to reconstruct the data correctly.

**Transmission Logic**: The sender reads the file.mp3 and divides it into 1020-byte chunks. For each packet, the sender:
1. Creates the packet with the sequence ID and data
2. Records the send timestamp for delay calculation
3. Transmits the packet to the receiver at localhost:5001
4. Sets a 1-second socket timeout and waits for an ACK

**Acknowledgment Handling**: When an ACK arrives, the sender checks if the acknowledged sequence ID is greater than the current packet's sequence ID (cumulative ACK). If so, the packet is considered delivered. If a timeout occurs, the packet is retransmitted.

**Termination**: After all data packets are acknowledged, the sender sends an empty packet (sequence ID = total file size), waits for the receiver's FIN message, and responds with FINACK to complete the connection teardown.

**Metrics Collection**: Throughput is calculated as total_bytes / total_time. Per-packet delay is measured from the first send attempt to final ACK receipt. The performance metric combines both: 0.3 * (throughput/1000) + 0.7 / avg_delay.

**External Sources**: None

### Results

| Metric | Average | Standard Deviation |
|--------|---------|-------------------|
| Throughput (bytes/sec) | ___________ | ___________ |
| Avg Packet Delay (sec) | ___________ | ___________ |
| Performance Metric | ___________ | ___________ |

**Output Screenshot**: [Insert screenshot here]

---

## 2. Fixed Sliding Window Protocol

### Technical Explanation

The Fixed Sliding Window protocol significantly improves throughput over Stop-and-Wait by allowing multiple packets in flight simultaneously. Our implementation uses a window size of 100 packets.

**Window Management**: We maintain two pointers: `window_base` (the oldest unacknowledged packet) and `next_to_send` (the next packet to transmit). Packets are sent as long as (next_to_send - window_base) < WINDOW_SIZE and data remains.

**Cumulative ACKs**: The receiver sends cumulative acknowledgments indicating the next expected byte offset. When an ACK is received, the sender slides the window forward by advancing window_base to match the ACK. This efficiently handles out-of-order delivery since multiple packets can be acknowledged with a single ACK.

**Packet Loss Handling**: On socket timeout (1 second), we retransmit all unacknowledged packets currently in the window (Go-Back-N behavior). This ensures reliability even with the network profile's variable packet loss rate (0-20%).

### Window Adjustment Technique

Unlike TCP Reno, the Fixed Sliding Window maintains a constant window size of 100 packets regardless of network conditions. The window advances only when cumulative ACKs arrive:

1. If ACK_id > seq_id of packet at window_base: slide window forward
2. Track all packets between old and new window_base as acknowledged
3. Send new packets to fill the window up to WINDOW_SIZE

This simplicity makes it easier to implement but less adaptive than TCP's dynamic congestion control.

**Delay Tracking**: We record the first send time for each packet and the time when its ACK is received. For retransmitted packets, the delay is measured from the original send time, as specified in the assignment.

**External Sources**: None

### Results

| Metric | Average | Standard Deviation |
|--------|---------|-------------------|
| Throughput (bytes/sec) | ___________ | ___________ |
| Avg Packet Delay (sec) | ___________ | ___________ |
| Performance Metric | ___________ | ___________ |

**Output Screenshot**: [Insert screenshot here]

---

## 3. TCP Reno (Extra Credit)

### Technical Explanation

TCP Reno implements adaptive congestion control with slow start, congestion avoidance, and fast recovery mechanisms.

**Slow Start Threshold**: The initial ssthresh is set to 64 packets. When cwnd < ssthresh, the sender is in slow start mode, doubling the congestion window each RTT (by incrementing cwnd by 1 for each ACK).

**AIMD Implementation**: 
- **Additive Increase**: In congestion avoidance (cwnd >= ssthresh), cwnd increases by 1/cwnd for each ACK, resulting in approximately one packet increase per RTT.
- **Multiplicative Decrease**: On timeout, ssthresh = cwnd/2 and cwnd = 1 (back to slow start).

**Fast Retransmit and Fast Recovery**:
1. Track duplicate ACKs (ACKs with the same sequence number as the last)
2. On 3 duplicate ACKs: ssthresh = cwnd/2, cwnd = ssthresh + 3, retransmit the lost packet
3. During fast recovery, each additional duplicate ACK inflates cwnd by 1
4. On receiving a new ACK, exit fast recovery and set cwnd = ssthresh

### Handling Congestion

Example scenario:
- cwnd grows from 1 → 2 → 4 → 8 → ... → 64 (slow start)
- At cwnd = 64 (ssthresh), switch to congestion avoidance
- cwnd grows linearly: 64 → 65 → 66 → ...
- On 3 dup ACKs at cwnd = 80: ssthresh = 40, cwnd = 43, retransmit lost packet
- New ACK arrives: cwnd = 40, continue linear growth

**External Sources**: None

### Results

| Metric | Average | Standard Deviation |
|--------|---------|-------------------|
| Throughput (bytes/sec) | ___________ | ___________ |
| Avg Packet Delay (sec) | ___________ | ___________ |
| Performance Metric | ___________ | ___________ |

**Output Screenshot**: [Insert screenshot here]

---

## Submission Certification

I certify that all submitted work is my own work. I have completed all of the assignments on my own without assistance from others except as indicated by appropriate citation. I have read and understand the university policy on plagiarism and academic dishonesty.

**Team Member 1 Contributions**: ________________________________

| Full Name | Signature | Date |
|-----------|-----------|------|
| | | |

**Team Member 2 Contributions**: ________________________________

| Full Name | Signature | Date |
|-----------|-----------|------|
| | | |
