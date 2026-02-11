#!/bin/bash
# Comprehensive runner: runs all 3 sender scripts (10 iterations each)
# and saves results to separate .txt files.

DOCKER_DIR="project_1/2024_congestion_control_ecs152a/docker"
NUM_ITERATIONS=10

# List of sender scripts and their output files
SENDERS=("sender_stop_and_wait.py" "sender_fixed_sliding_window.py" "sender_reno.py")
OUTPUTS=("stop_and_wait_output.txt" "sliding_window_output.txt" "reno_output.txt")

for idx in "${!SENDERS[@]}"; do
    SENDER="${SENDERS[$idx]}"
    OUTPUT="${OUTPUTS[$idx]}"

    echo "========================================================"
    echo "  Running: $SENDER"
    echo "  Output file: $OUTPUT"
    echo "========================================================"

    # Clear the output file
    > "$OUTPUT"

    # Arrays to store results
    declare -a throughputs=()
    declare -a delays=()

    for i in $(seq 1 $NUM_ITERATIONS); do
        echo "--- Iteration $i of $NUM_ITERATIONS ---"

        # Stop any existing simulator
        docker stop ecs152a-simulator 2>/dev/null 1>/dev/null
        docker rm ecs152a-simulator 2>/dev/null 1>/dev/null
        sleep 1

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

        # Write to output file
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

    # Calculate averages using Python
    T_LIST=$(IFS=,; echo "${throughputs[*]}")
    D_LIST=$(IFS=,; echo "${delays[*]}")

    AVERAGES=$(python3 << EOF
throughputs = [${T_LIST}]
delays = [${D_LIST}]

if throughputs and delays:
    avg_throughput = sum(throughputs) / len(throughputs)
    avg_delay = sum(delays) / len(delays)
    metric = 0.3 * (avg_throughput / 1000) + 0.7 / avg_delay if avg_delay > 0 else 0
    print(f"Avg Throughput: {avg_throughput:.7f}")
    print(f"Avg Delay: {avg_delay:.7f}")
    print(f"Performance Metric: {metric:.7f}")
else:
    print("Error: No valid results collected")
EOF
)

    echo ""
    echo "=== Final Results for $SENDER ==="
    echo "$AVERAGES"

    # Append final results to output file
    echo "=== Final Results ===" >> "$OUTPUT"
    echo "$AVERAGES" >> "$OUTPUT"

    echo ""
    echo "Results saved to: $OUTPUT"
    echo ""

    # Reset arrays
    unset throughputs
    unset delays
done

echo "========================================================"
echo "  ALL DONE! Results saved to:"
echo "    - stop_and_wait_output.txt"
echo "    - sliding_window_output.txt"
echo "    - reno_output.txt"
echo "========================================================"
