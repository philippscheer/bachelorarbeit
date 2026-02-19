#!/bin/bash

# Check if any parameters were provided
if [ $# -eq 0 ]; then
    echo "No parameters provided."
    exit 1
fi

echo "Count of parameters: $#"
echo "-----------------------"

# Loop through and print each one
count=1
for arg in "$@"; do
    echo "Parameter $count: $arg"
    ((count++))
done