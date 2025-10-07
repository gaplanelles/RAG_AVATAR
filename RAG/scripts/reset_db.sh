#!/bin/bash

# Set error handling
set -e

# Source the read_env function
source scripts/read_env.sh

# Configuration
PORT=$(read_env_var "BACKEND_PORT")
CONDA_ENV="RAG"
DB_PATH="chroma_db"
CHUNKS_PATH="chunks"
LOG_DIR="logs"
APP_MODULE="src.rag_app.main:app"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Kill processes on port 9003
log_message "Killing processes on port $PORT..."
if lsof -ti :$PORT > /dev/null; then
    lsof -ti :$PORT | xargs kill -9
    log_message "Processes killed successfully"
else
    log_message "No processes found on port $PORT"
fi

# Remove ChromaDB directory
log_message "Removing ChromaDB directory..."
if [ -d "$DB_PATH" ]; then
    rm -rf "$DB_PATH" "$CHUNKS_PATH"
    log_message "ChromaDB directory removed successfully"
else
    log_message "ChromaDB directory not found"
fi

# Activate conda environment
log_message "Activating conda environment $CONDA_ENV..."
eval "$(conda shell.bash hook)"
if conda activate "$CONDA_ENV"; then
    log_message "Conda environment activated successfully"
else
    log_message "Failed to activate conda environment"
    exit 1
fi

# Start the application
log_message "Starting the application..."
TIMESTAMP=$(date "+%Y.%m.%d-%H.%M.%S")
nohup uvicorn "$APP_MODULE" \
    --host 0.0.0.0 \
    --port "$PORT" \
    --reload \
    > "$LOG_DIR/rag_port_${PORT}_${TIMESTAMP}.log" 2>&1 &

# Check if the application started successfully with retries
MAX_RETRIES=10
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    sleep 2
    if lsof -ti :$PORT > /dev/null; then
        log_message "Application started successfully on port $PORT"
        log_message "Logs available at: $LOG_DIR/rag_port_${PORT}_${TIMESTAMP}.log"
        exit 0
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    log_message "Waiting for application to start... (attempt $RETRY_COUNT/$MAX_RETRIES)"
done

log_message "Failed to start the application after $MAX_RETRIES attempts"
exit 1