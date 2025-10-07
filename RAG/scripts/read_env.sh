#!/bin/bash

read_env_var() {
    local var_name=$1
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local env_file="$script_dir/../.env"

    if [ ! -f "$env_file" ]; then
        echo "Error: .env file not found in the project root directory" >&2
        exit 1
    fi
    
    local value=$(grep "^${var_name}=" "$env_file" | cut -d '=' -f2-)
    if [ -z "$value" ]; then
        echo "Error: ${var_name} not found in .env file" >&2
        exit 1
    fi
    
    echo "$value"
} 

