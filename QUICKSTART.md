# Quick Start Guide - 5 Minutes Setup

Get NS3 5G NR simulations running in 5 minutes!

## 🚀 One-Command Setup

```bash
# Clone and run setup script
git clone https://github.com/sksayed/ns3_project_for_kit.git
cd ns3_project_for_kit
./setup.sh
```

The script will:
- ✓ Check and install dependencies
- ✓ Configure correct NS-3 version (3.45)
- ✓ Set up NR module
- ✓ Build the project
- ✓ Verify installation

**Time**: ~20-30 minutes (mostly compilation)

## 🎯 Manual Setup (If Script Fails)

### 1. Install Dependencies
```bash
sudo apt update
sudo apt install -y build-essential cmake ninja-build git \
    python3 python3-dev libgtk-3-dev libxml2 libxml2-dev \
    libsqlite3-dev libeigen3-dev libboost-all-dev
```

### 2. Clone and Configure
```bash
git clone https://github.com/sksayed/ns3_project_for_kit.git
cd ns3_project_for_kit

# Checkout correct version
git remote add ns-3-official https://gitlab.com/nsnam/ns-3-dev.git
git fetch ns-3-official --tags
git checkout ns-3.45

# Restore custom code
git checkout 5g_implementation -- 5g/ CMakeLists.txt
```

### 3. Verify NR Module
```bash
ls contrib/nr/
# Should show: CMakeLists.txt, examples/, helper/, model/

# If not there, move it:
mv nr contrib/  # if in root
```

### 4. Build
```bash
./ns3 configure --enable-examples --enable-tests
./ns3 build -j4
```

## ✅ Test Installation

```bash
# Test 1: Basic NS-3
./ns3 run --no-build first

# Test 2: NR Module
./ns3 run --no-build cttc-nr-demo

# Test 3: Custom 5G Simulation
./build/5g/ns3.45-nr_playfield_traces-default
```

All tests should run without errors!

## 📊 Run Your First Simulation

```bash
# Run 5G simulation
./build/5g/ns3.45-nr_playfield_traces-default

# Check results
ls 5g_outputs/
# You'll see: flowmon XML, PCAP files, NetAnim files
```

## 🆘 Common Issues

**Build Killed/Out of Memory?**
```bash
./ns3 build -j2  # Use fewer parallel jobs
```

**TypeId Error at Runtime?**
```bash
# Wrong NS-3 version - fix it:
git checkout ns-3.45
./ns3 clean && ./ns3 configure --enable-examples --enable-tests
./ns3 build -j4
```

**NR Module Not Found?**
```bash
# Clone NR module:
cd contrib/
git clone https://gitlab.com/cttc-lena/nr.git
cd nr && git checkout v4.1 && cd ../..
./ns3 configure --enable-examples --enable-tests
```

## 📚 Next Steps

- Read full documentation: `README_PROJECT.md`
- Explore examples: `contrib/nr/examples/`
- Modify simulations: `5g/src/nr_playfield_traces.cc`
- Analyze results: `5g_outputs/`

## 🔑 Key Commands

```bash
# List all available programs
./ns3 show targets

# Run without rebuilding
./ns3 run --no-build <program-name>

# Build after code changes (fast!)
./ns3 build -j4

# Clean everything
./ns3 clean
```

## ⚡ Pro Tips

1. **First build is slow** (~30 min), subsequent builds are fast (~1 min)
2. **Use `--no-build`** when running to skip unnecessary rebuilds
3. **Save memory** by using `-j2` or `-j4` instead of `-j$(nproc)`
4. **Check versions**: NS-3 must be `3.45`, NR must be `v4.1`

## 📁 Important Files

```
ns3_project_for_kit/
├── setup.sh              ← Run this first!
├── README_PROJECT.md     ← Full documentation
├── QUICKSTART.md        ← This file
├── 5g/src/              ← Your 5G simulations
├── contrib/nr/          ← NR module (v4.1)
└── 5g_outputs/          ← Simulation results
```

## ✨ You're Ready!

Your NS-3 5G NR simulation environment is ready to use!

Need help? Check `README_PROJECT.md` for detailed troubleshooting.

