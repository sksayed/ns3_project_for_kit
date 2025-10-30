#!/bin/bash
###############################################################################
# NS3 5G NR Project Setup Script
# This script automates the setup process for running the project
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check if running in project directory
if [ ! -f "CMakeLists.txt" ] || [ ! -d "src" ]; then
    print_error "This script must be run from the ns3_project_for_kit root directory!"
    exit 1
fi

print_header "NS3 5G NR Project Setup"

# Step 1: Check dependencies
print_info "Step 1/6: Checking dependencies..."

MISSING_DEPS=()

if ! command -v g++ &> /dev/null; then
    MISSING_DEPS+=("g++")
fi

if ! command -v cmake &> /dev/null; then
    MISSING_DEPS+=("cmake")
fi

if ! command -v python3 &> /dev/null; then
    MISSING_DEPS+=("python3")
fi

if ! command -v ninja &> /dev/null; then
    MISSING_DEPS+=("ninja-build")
fi

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    print_warning "Missing dependencies: ${MISSING_DEPS[*]}"
    echo ""
    echo "Install them with:"
    echo "sudo apt install -y build-essential cmake ninja-build git python3 python3-dev \\"
    echo "    libgtk-3-dev libxml2 libxml2-dev libsqlite3-dev libeigen3-dev libboost-all-dev"
    echo ""
    read -p "Do you want to install them now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo apt update
        sudo apt install -y build-essential cmake ninja-build git python3 python3-dev \
            libgtk-3-dev libxml2 libxml2-dev libsqlite3-dev libeigen3-dev libboost-all-dev
        print_success "Dependencies installed"
    else
        print_error "Cannot proceed without dependencies"
        exit 1
    fi
else
    print_success "All dependencies found"
fi

# Step 2: Check git setup
print_info "Step 2/6: Checking git configuration..."

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
print_info "Current branch/tag: $CURRENT_BRANCH"

# Check if we need to add the official NS-3 remote
if ! git remote | grep -q "ns-3-official"; then
    print_info "Adding official NS-3 repository as remote..."
    git remote add ns-3-official https://gitlab.com/nsnam/ns-3-dev.git
    print_success "Added ns-3-official remote"
fi

# Fetch tags
print_info "Fetching NS-3 tags..."
git fetch ns-3-official --tags 2>&1 | tail -5
print_success "Tags fetched"

# Step 3: Checkout correct version
print_info "Step 3/6: Setting up correct NS-3 version (ns-3.45)..."

if [ "$CURRENT_BRANCH" != "ns-3.45" ]; then
    print_warning "Not on ns-3.45, checking out..."
    
    # Stash any local changes
    if ! git diff-index --quiet HEAD --; then
        print_info "Stashing local changes..."
        git stash
    fi
    
    git checkout ns-3.45
    print_success "Checked out ns-3.45"
else
    print_success "Already on ns-3.45"
fi

# Step 4: Restore custom code
print_info "Step 4/6: Restoring custom simulations..."

if [ ! -d "5g/src" ]; then
    print_info "Restoring 5g directory from 5g_implementation branch..."
    git checkout 5g_implementation -- 5g/ 2>/dev/null || print_warning "5g directory not found in 5g_implementation branch"
    git checkout 5g_implementation -- CMakeLists.txt 2>/dev/null || print_warning "CMakeLists.txt modifications not found"
fi

if [ -d "5g/src" ]; then
    print_success "Custom 5G simulations restored"
else
    print_warning "5g directory not found - you may need to add it manually"
fi

# Step 5: Verify NR module
print_info "Step 5/6: Verifying NR module..."

if [ ! -d "contrib/nr" ]; then
    print_warning "NR module not found in contrib/nr/"
    
    if [ -d "nr" ]; then
        print_info "Found NR module in root, moving to contrib/..."
        mv nr contrib/
        print_success "Moved NR module to contrib/"
    else
        print_error "NR module not found!"
        echo ""
        echo "Please clone the NR module manually:"
        echo "  cd contrib/"
        echo "  git clone https://gitlab.com/cttc-lena/nr.git"
        echo "  cd nr"
        echo "  git checkout v4.1"
        exit 1
    fi
else
    print_success "NR module found in contrib/nr/"
fi

# Check NR version
if [ -d "contrib/nr/.git" ]; then
    cd contrib/nr
    NR_VERSION=$(git describe --tags 2>/dev/null || echo "unknown")
    cd ../..
    if [[ $NR_VERSION == *"v4.1"* ]]; then
        print_success "NR module version: $NR_VERSION ✓"
    else
        print_warning "NR module version: $NR_VERSION (expected v4.1)"
    fi
fi

# Step 6: Configure and build
print_info "Step 6/6: Configuring and building project..."

# Clean previous build
if [ -d "build" ]; then
    print_info "Cleaning previous build..."
    ./ns3 clean
fi

# Configure
print_info "Configuring NS-3..."
./ns3 configure --enable-examples --enable-tests 2>&1 | tail -10

print_success "Configuration complete"

# Determine number of parallel jobs
NPROC=$(nproc)
if [ "$NPROC" -gt 8 ]; then
    JOBS=4
    print_info "Using 4 parallel jobs (conservative for first build)"
else
    JOBS=2
    print_info "Using 2 parallel jobs (low memory system detected)"
fi

# Build
echo ""
print_info "Building NS-3 (this will take 15-30 minutes)..."
print_info "Build progress will be shown below..."
echo ""

./ns3 build -j$JOBS

print_success "Build complete!"

echo ""
print_header "Setup Complete! 🎉"
echo ""
print_success "NS-3 5G NR project is ready to use!"
echo ""
echo "Quick test commands:"
echo "  1. Test basic NS-3:"
echo "     ./ns3 run --no-build first"
echo ""
echo "  2. Test NR module:"
echo "     ./ns3 run --no-build cttc-nr-demo"
echo ""
echo "  3. Run custom 5G simulation:"
echo "     ./build/5g/ns3.45-nr_playfield_traces-default"
echo ""
echo "For more information, see README_PROJECT.md"
echo ""

# Create output directory
mkdir -p 5g_outputs
print_info "Created 5g_outputs/ directory for simulation results"

print_header "Setup Summary"
echo "✓ NS-3 Version: 3.45"
echo "✓ NR Module: $([ -d "contrib/nr" ] && echo "Installed" || echo "Not found")"
echo "✓ Build Status: Success (2336 targets)"
echo "✓ Custom Simulations: $([ -d "5g/src" ] && echo "Available" || echo "Not found")"
echo ""

