#!/bin/bash

# NeuroShield Quick Setup Script
# This script sets up the complete NeuroShield environment

set -e  # Exit on error

echo "================================================"
echo "  NeuroShield Setup Script"
echo "  EEG-Based Addiction Recovery Support"
echo "================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo -e "${RED}✗ Python 3.8 or higher is required. Found: $python_version${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python $python_version detected${NC}"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment already exists. Skipping...${NC}"
else
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install dependencies
echo ""
echo "Installing Python dependencies..."
pip install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Create necessary directories
echo ""
echo "Creating project directories..."
mkdir -p uploads models templates static
echo -e "${GREEN}✓ Directories created${NC}"

# Initialize database
echo ""
echo "Initializing database..."
python db_setup.py
echo -e "${GREEN}✓ Database initialized${NC}"

# Train ML model
echo ""
echo "Training ML model (this may take a minute)..."
python train_model.py
echo -e "${GREEN}✓ Model trained and saved${NC}"

# Check if templates exist
if [ ! -f "templates/index.html" ]; then
    echo -e "${YELLOW}⚠ Warning: templates/index.html not found${NC}"
    echo "Please ensure all HTML templates are in the templates/ directory"
fi

# Check if static files exist
if [ ! -f "static/app.js" ]; then
    echo -e "${YELLOW}⚠ Warning: static/app.js not found${NC}"
    echo "Please ensure all JavaScript files are in the static/ directory"
fi

# Summary
echo ""
echo "================================================"
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Start the Flask server:"
echo "   python app.py"
echo ""
echo "3. Open your browser to:"
echo "   http://localhost:5000"
echo ""
echo "4. Login with demo credentials:"
echo "   Username: demo_user"
echo "   Password: demo123"
echo ""
echo "================================================"
echo "For more information, see README.md"
echo "================================================"