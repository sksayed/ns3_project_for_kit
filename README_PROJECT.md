# NS3 5G NR Simulation Project

This project contains NS-3.45 network simulator with integrated 5G NR module and custom simulation scenarios including WiFi, LTE, and 5G NR networks.

## 🎯 Project Overview

This repository includes:
- **NS-3.45**: Network Simulator 3 (release version 3.45)
- **NR Module v4.1**: 5G New Radio module for 3GPP NR simulations
- **Custom 5G Simulations**: Located in `5g/src/` directory
- **WiFi Mesh Analysis**: Tools and simulations for WiFi mesh networks
- **LTE Analysis**: LTE network simulation and analysis tools

## 📋 Prerequisites

### System Requirements
- **OS**: Linux (Ubuntu 20.04/22.04/24.04 recommended) or WSL2 on Windows
- **Compiler**: g++-11 or later, OR clang++-17 or later
- **Python**: 3.8 or later
- **CMake**: 3.20 or later
- **RAM**: At least 8GB (16GB recommended for parallel builds)
- **Disk Space**: ~5GB for full build

### Required Dependencies

Install dependencies on Ubuntu/Debian:

```bash
# Essential build tools
sudo apt update
sudo apt install -y build-essential cmake ninja-build git

# NS-3 dependencies
sudo apt install -y \
    python3 python3-dev \
    libgtk-3-dev \
    libxml2 libxml2-dev \
    libsqlite3-dev \
    libeigen3-dev \
    libboost-all-dev
```

## 🚀 Quick Start Guide

### 1. Clone the Repository

```bash
git clone https://github.com/sksayed/ns3_project_for_kit.git
cd ns3_project_for_kit
```

### 2. Checkout the Correct Version

**IMPORTANT**: This project requires **NS-3.45** to work with NR module v4.1.

```bash
# Add official NS-3 remote (if not already added)
git remote add ns-3-official https://gitlab.com/nsnam/ns-3-dev.git

# Fetch tags
git fetch ns-3-official --tags

# Checkout ns-3.45
git checkout ns-3.45
```

### 3. Restore Custom Code

The 5G simulations and custom modules need to be restored from the development branch:

```bash
# Restore 5g directory with custom simulations
git checkout 5g_implementation -- 5g/

# Restore CMakeLists.txt modifications
git checkout 5g_implementation -- CMakeLists.txt
```

Alternatively, if you cloned from a specific branch with everything configured:

```bash
# Clone with the working configuration
git clone -b 5g_implementation https://github.com/sksayed/ns3_project_for_kit.git
cd ns3_project_for_kit

# Then checkout ns-3.45 base
git checkout ns-3.45
git checkout 5g_implementation -- 5g/ CMakeLists.txt contrib/
```

### 4. Verify NR Module Location

The NR module should be in `contrib/nr/` directory:

```bash
ls contrib/nr/
# Should show: CMakeLists.txt, examples/, helper/, model/, etc.
```

If the NR module is missing or in the wrong location:

```bash
# If it's in the root 'nr/' directory, move it:
mv nr contrib/

# If it's completely missing, clone it:
cd contrib/
git clone https://gitlab.com/cttc-lena/nr.git
cd nr
git checkout v4.1
cd ../..
```

### 5. Configure the Build

```bash
./ns3 configure --enable-examples --enable-tests
```

**Expected output**: You should see "nr" listed in "Modules configured to be built"

### 6. Build the Project

For systems with limited RAM (< 16GB):
```bash
./ns3 build -j4
```

For systems with more RAM:
```bash
./ns3 build -j$(nproc)
```

**Build time**: 
- First build: ~15-30 minutes (2336 targets)
- Subsequent builds: ~30-60 seconds (only changed files)

**Expected output**: `[2336/2336]` all targets compiled successfully

## 🏃 Running Simulations

### List Available Programs

```bash
./ns3 show targets | grep -E "5g|nr|wifi|lte"
```

### Run Basic NS-3 Examples

```bash
# Basic tutorial
./ns3 run --no-build first

# WiFi example
./ns3 run --no-build wifi-simple-adhoc

# LTE example
./ns3 run --no-build lena-simple-epc
```

### Run NR Module Examples

```bash
# Basic NR demo
./ns3 run --no-build cttc-nr-demo

# NR with multiple flows
./ns3 run --no-build cttc-nr-multi-flow-qos-sched
```

### Run Custom 5G Simulations

```bash
# 5G NR simulation with mobility and traffic
./build/5g/ns3.45-nr_playfield_traces-default

# Basic 5G NR simulation
./build/5g/ns3.45-nr_simulation-default
```

**Output location**: Results are saved to `5g_outputs/` directory

## 📁 Project Structure

```
ns3_project_for_kit/
├── 5g/                          # Custom 5G simulations
│   ├── src/
│   │   ├── nr_playfield_traces.cc    # Main 5G simulation with mobility
│   │   └── nr_simulation.cc          # Basic 5G simulation
│   ├── scripts/                      # Helper scripts
│   └── README.md
├── contrib/
│   └── nr/                      # 5G NR module (v4.1)
├── src/                         # NS-3 core modules
├── examples/                    # NS-3 example programs
├── wifi_mesh_analyzer/          # WiFi mesh analysis tools
├── lte_analyzer/                # LTE analysis tools
└── scratch/                     # User simulation scripts
```

## ⚙️ Version Compatibility

| Component | Version | Branch/Tag | Compatibility |
|-----------|---------|------------|---------------|
| NS-3 | 3.45 | `ns-3.45` | ✅ Required |
| NR Module | 4.1 | `v4.1` | ✅ Required |
| Custom Code | - | `5g_implementation` | ✅ Working |

**⚠️ IMPORTANT**: 
- NS-3 `3-dev` (development) does NOT work with NR v4.1
- Always use `ns-3.45` tag for this project
- The NR module MUST be in `contrib/nr/` directory

## 🐛 Troubleshooting

### Build Fails with "Killed" Error

**Problem**: Compiler processes killed during build

**Solution**: Reduce parallel jobs
```bash
./ns3 build -j2  # Use only 2 parallel jobs
```

### "Couldn't find the specified program" Error

**Problem**: NS-3 can't find your executable

**Solution**: Run directly with full path
```bash
./build/5g/ns3.45-nr_playfield_traces-default
```

Or use `--no-build` flag:
```bash
./ns3 run --no-build cttc-nr-demo
```

### TypeId Initialization Error

**Problem**: Runtime error about uninitialized TypeId

**Cause**: Version mismatch between NS-3 and NR module

**Solution**: Ensure you're on `ns-3.45`:
```bash
git checkout ns-3.45
./ns3 clean
./ns3 configure --enable-examples --enable-tests
./ns3 build -j4
```

### NR Module Not Found

**Problem**: CMake doesn't detect NR module

**Solution**: Verify NR module location
```bash
# Check if it exists
ls contrib/nr/CMakeLists.txt

# If not, clone it
cd contrib/
git clone https://gitlab.com/cttc-lena/nr.git
cd nr
git checkout v4.1
cd ../..
./ns3 configure --enable-examples --enable-tests
```

### Missing Dependencies

**Problem**: Build fails with missing library errors

**Solution**: Install all dependencies
```bash
sudo apt install -y build-essential cmake ninja-build git \
    python3 python3-dev libgtk-3-dev libxml2 libxml2-dev \
    libsqlite3-dev libeigen3-dev libboost-all-dev
```

## 🔧 Development Workflow

### Making Changes to Simulations

1. Edit your simulation file (e.g., `5g/src/nr_playfield_traces.cc`)
2. Rebuild (only changed files will be recompiled):
   ```bash
   ./ns3 build -j4
   ```
3. Run your simulation:
   ```bash
   ./build/5g/ns3.45-nr_playfield_traces-default
   ```

### Creating New Simulations

1. Add your `.cc` file to `5g/src/` or `scratch/`
2. For `5g/src/`: CMakeLists.txt will auto-detect it
3. For `scratch/`: Place directly in `scratch/` directory
4. Rebuild:
   ```bash
   ./ns3 build -j4
   ```

### Switching Between Branches

```bash
# Save your work
git stash

# Switch to another branch
git checkout <branch-name>

# Restore your work
git stash pop

# Rebuild
./ns3 clean
./ns3 configure --enable-examples --enable-tests
./ns3 build -j4
```

## 📊 Output Files

Simulations generate various output files:

### 5G Simulations
- **Location**: `5g_outputs/`
- **Files**:
  - `flowmon-nr-playfield-rw.xml` - FlowMonitor statistics
  - `netanim-nr-playfield-rw.xml` - NetAnim visualization
  - `nr_playfield_rw_pcap-*.pcap` - PCAP traces
  - `ipv4-l3.tr` - IPv4 routing traces

### Analyzing Results

Use FlowMonitor for detailed statistics:
```bash
# View flow statistics
flowmon-parse 5g_outputs/flowmon-nr-playfield-rw.xml
```

Use Wireshark for packet analysis:
```bash
wireshark 5g_outputs/nr_playfield_rw_pcap-0-0.pcap
```

## 📚 Additional Resources

### Official Documentation
- **NS-3 Manual**: https://www.nsnam.org/documentation/
- **NS-3 Tutorial**: https://www.nsnam.org/docs/tutorial/html/
- **NR Module**: https://5g-lena.cttc.es/
- **NR GitLab**: https://gitlab.com/cttc-lena/nr

### Example Simulations
- Basic examples: `examples/tutorial/`
- WiFi examples: `examples/wireless/`
- LTE examples: `src/lte/examples/`
- NR examples: `contrib/nr/examples/`

## 🤝 Contributing

When contributing:
1. Work on the `5g_implementation` branch
2. Test on `ns-3.45` base
3. Commit only simulation code, not NS-3 core changes
4. Document new simulations in `5g/README.md`

## 📝 License

- **NS-3**: GNU GPLv2
- **NR Module**: GNU GPLv2
- **Custom Simulations**: Check individual file headers

## 👤 Authors

- NS-3 Project: https://www.nsnam.org
- NR Module: CTTC (Centre Tecnològic de Telecomunicacions de Catalunya)
- Custom Simulations: [Your Team/Name]

## 🆘 Support

For issues:
1. Check this README's troubleshooting section
2. Review NS-3 documentation: https://www.nsnam.org/documentation/
3. NR module issues: https://gitlab.com/cttc-lena/nr/-/issues
4. Project-specific issues: [Your issue tracker]

---

**Last Updated**: October 2025  
**Tested On**: Ubuntu 22.04, WSL2 Ubuntu 22.04  
**NS-3 Version**: 3.45  
**NR Module Version**: 4.1

