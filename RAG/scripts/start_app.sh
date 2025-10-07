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

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Get the existing log file path
LOG_FILE="$LOG_DIR/rag_port_${PORT}_sept.log"

# Define paths to SSL certificate and key
SSL_CERTFILE="$PROJECT_ROOT/certs/cert.pem"
SSL_KEYFILE="$PROJECT_ROOT/certs/key.pem"

# Start the application
cd "$PROJECT_ROOT"
nohup uvicorn src.rag_app.main:app --host 0.0.0.0 --port $PORT --reload --ssl-keyfile $SSL_KEYFILE --ssl-certfile $SSL_CERTFILE >> "$LOG_FILE" 2>&1 &

# Get the PID of the last background process
PID=$!

echo "Application started with PID: $PID"
echo "Log file: $LOG_FILE" 