#!/bin/bash

# Set error handling
set -e

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Source the read_env function
source "$SCRIPT_DIR/read_env.sh"

# Configuration
PORT=$(read_env_var "BACKEND_PORT")
LOG_DIR="$PROJECT_ROOT/logs"
APP_MODULE="src.rag_app.main:app"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Get the existing log file path
LOG_FILE="$LOG_DIR/rag_port_${PORT}.log"

# Kill processes on port
log_message "Killing processes on port $PORT..."
if lsof -ti :$PORT > /dev/null; then
    lsof -ti :$PORT | xargs kill -9
    log_message "Processes killed successfully"
else
    log_message "No processes found on port $PORT"
fi

# Start the application
log_message "Starting the application..."
cd "$PROJECT_ROOT"  # Change to project root directory
nohup uvicorn "$APP_MODULE" \
    --host 0.0.0.0 \
    --port "$PORT" \
    --reload \
    >> "$LOG_FILE" 2>&1 &

# Check if the application started successfully with retries
MAX_RETRIES=10
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    sleep 2
    if lsof -ti :$PORT > /dev/null; then
        log_message "Application started successfully on port $PORT"
        log_message "Logs available at: $LOG_FILE"
        exit 0
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    log_message "Waiting for application to start... (attempt $RETRY_COUNT/$MAX_RETRIES)"
done

log_message "Failed to start the application after $MAX_RETRIES attempts"
exit 1