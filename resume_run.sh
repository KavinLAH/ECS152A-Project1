#!/bin/bash
# Resume script: finishes Stop-and-Wait (iterations 5-10), then runs all 10
# for Sliding Window and Reno. Saves results to separate .txt files.

DOCKER_DIR="project_1/2024_congestion_control_ecs152a/docker"

run_sender() {
    local SENDER="$1"
    local OUTPUT="$2"
    local START_ITER="$3"
    local NUM_ITERATIONS="$4"

    echo "========================================================"
    echo "  Running: $SENDER (iterations $START_ITER to $NUM_ITERATIONS)"
    echo "  Output file: $OUTPUT"
    echo "========================================================"

    # Arrays to store results
    local -a throughputs=()
    local -a delays=()

    for i in $(seq "$START_ITER" "$NUM_ITERATIONS"); do
        echo "--- Iteration $i of $NUM_ITERATIONS ---"

        # Stop any existing simulator
        docker stop ecs152a-simulator 2>/dev/null 1>/dev/null
        docker rm ecs152a-simulator 2>/dev/null 1>/dev/null
        sleep 2

        # Start simulator in background
        docker run --name="ecs152a-simulator" \
            --cap-add=NET_ADMIN \
            --rm \
            -p 5001:5001/udp \
            -v "$(pwd)/$DOCKER_DIR/hdd":/hdd \
            ecs152a/simulator > /dev/null 2>&1 &
        SIMULATOR_PID=$!

        # Wait for receiver to be ready
        sleep 5

        # Run sender and capture output
        RESULT=$(python3 "$SENDER" 2>/dev/null)

        # Parse output (line 1 = throughput, line 2 = delay, line 3 = metric)
        THROUGHPUT=$(echo "$RESULT" | sed -n '1p')
        DELAY=$(echo "$RESULT" | sed -n '2p')
        METRIC=$(echo "$RESULT" | sed -n '3p')

        echo "  Throughput: $THROUGHPUT"
        echo "  Delay: $DELAY"
        echo "  Metric: $METRIC"

        # Append to output file
        echo "=== Iteration $i of $NUM_ITERATIONS ===" >> "$OUTPUT"
        echo "Throughput: $THROUGHPUT" >> "$OUTPUT"
        echo "Delay: $DELAY" >> "$OUTPUT"
        echo "Metric: $METRIC" >> "$OUTPUT"
        echo "" >> "$OUTPUT"

        throughputs+=("$THROUGHPUT")
        delays+=("$DELAY")

        # Stop simulator
        docker stop ecs152a-simulator 2>/dev/null 1>/dev/null
        wait $SIMULATOR_PID 2>/dev/null
        sleep 1
    done

    echo ""
    echo "  Iterations $START_ITER-$NUM_ITERATIONS saved to: $OUTPUT"
    echo ""
}

compute_final_averages() {
    local OUTPUT="$1"
    local LABEL="$2"

    # Extract all throughputs and delays from the output file
    python3 << EOF
lines = open("$OUTPUT").readlines()
throughputs = []
delays = []
for line in lines:
    if line.startswith("Throughput:"):
        val = line.split(":")[1].strip()
        if val:
            throughputs.append(float(val))
    elif line.startswith("Delay:"):
        val = line.split(":")[1].strip()
        if val:
            delays.append(float(val))

if throughputs and delays:
    avg_t = sum(throughputs) / len(throughputs)
    avg_d = sum(delays) / len(delays)
    metric = 0.3 * (avg_t / 1000) + 0.7 / avg_d if avg_d > 0 else 0
    result = f"Avg Throughput: {avg_t:.7f}\nAvg Delay: {avg_d:.7f}\nPerformance Metric: {metric:.7f}"
    print(result)
    with open("$OUTPUT", "a") as f:
        f.write("=== Final Results ===\n")
        f.write(result + "\n")
else:
    print("Error: No valid results collected")
EOF
}

# ============================================================
# 1) STOP-AND-WAIT: Resume from iteration 5 (1-4 already done)
# ============================================================
run_sender "sender_stop_and_wait.py" "stop_and_wait_output.txt" 5 10

echo "=== Computing Stop-and-Wait final averages ==="
compute_final_averages "stop_and_wait_output.txt" "Stop-and-Wait"
echo ""

# ============================================================
# 2) FIXED SLIDING WINDOW: Full run (iterations 1-10)
# ============================================================
> sliding_window_output.txt
run_sender "sender_fixed_sliding_window.py" "sliding_window_output.txt" 1 10

echo "=== Computing Sliding Window final averages ==="
compute_final_averages "sliding_window_output.txt" "Fixed Sliding Window"
echo ""

# ============================================================
# 3) TCP RENO: Full run (iterations 1-10)
# ============================================================
> reno_output.txt
run_sender "sender_reno.py" "reno_output.txt" 1 10

echo "=== Computing TCP Reno final averages ==="
compute_final_averages "reno_output.txt" "TCP Reno"
echo ""

# ============================================================
echo "========================================================"
echo "  ALL DONE! Results saved to:"
echo "    - stop_and_wait_output.txt  (10 iterations)"
echo "    - sliding_window_output.txt (10 iterations)"
echo "    - reno_output.txt           (10 iterations)"
echo "========================================================"
