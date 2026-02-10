#!/bin/bash
# Runner script that handles simulator restart between iterations
# Usage: ./run_all.sh <sender_script.py>

SENDER_SCRIPT=${1:-sender_reno.py}
NUM_ITERATIONS=10
DOCKER_DIR="project_1/2024_congestion_control_ecs152a/docker"

# Arrays to store results
declare -a throughputs
declare -a delays

for i in $(seq 1 $NUM_ITERATIONS); do
    # Stop any existing simulator (suppress output)
    docker stop ecs152a-simulator 2>/dev/null 1>/dev/null
    docker rm ecs152a-simulator 2>/dev/null 1>/dev/null

    # Start simulator in background (suppress all docker/build output)
    cd "$DOCKER_DIR"
    ./start-simulator.sh > /dev/null 2>&1 &
    SIMULATOR_PID=$!
    cd - > /dev/null

    # Wait for receiver to be ready
    sleep 3

    # Run sender and capture output (suppress stderr to hide docker warnings)
    OUTPUT=$(python3 "$SENDER_SCRIPT" 2>/dev/null)

    # Parse output (expects: throughput, delay, metric on separate lines)
    THROUGHPUT=$(echo "$OUTPUT" | head -1)
    DELAY=$(echo "$OUTPUT" | head -2 | tail -1)

    echo "=== Iteration $i of $NUM_ITERATIONS ==="
    echo "Throughput: $THROUGHPUT"
    echo "Delay: $DELAY"

    throughputs+=("$THROUGHPUT")
    delays+=("$DELAY")

    # Wait for simulator to finish
    wait $SIMULATOR_PID 2>/dev/null

done

# Convert bash arrays to comma-separated strings for Python
T_LIST=$(IFS=,; echo "${throughputs[*]}")
D_LIST=$(IFS=,; echo "${delays[*]}")

# Calculate averages using Python
echo ""
echo "=== Final Results ==="
python3 << EOF
throughputs = [${T_LIST}]
delays = [${D_LIST}]

if throughputs and delays:
    avg_throughput = sum(throughputs) / len(throughputs)
    avg_delay = sum(delays) / len(delays)

    # Performance metric from assignment
    metric = 0.3 * (avg_throughput / 1000) + 0.7 / avg_delay if avg_delay > 0 else 0

    print(f"Avg Throughput: {avg_throughput:.7f}")
    print(f"Avg Delay: {avg_delay:.7f}")
    print(f"Performance Metric: {metric:.7f}")
else:
    print("Error: No valid results collected")
EOF
