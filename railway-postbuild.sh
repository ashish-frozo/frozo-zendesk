#!/bin/bash

# Post-build script for Railway
# Runs after dependencies are installed

echo "Running post-build setup..."

# Download spaCy English model (required for NER)
echo "Downloading spaCy English language model..."
python -m spacy download en_core_web_lg

echo "Post-build complete!"
