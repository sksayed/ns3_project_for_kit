#ifndef REPORT_UTILS_H
#define REPORT_UTILS_H

#include <cstdint>
#include <iosfwd>
#include <string>
#include <vector>

struct SimulationMetadata
{
    std::string scenarioName;
    std::string environment;      // e.g., "400m x 400m x 30m urban playfield"
    std::string topologySummary;  // e.g., "2 gNBs (macro, static) + 10 UEs"
    std::string mobilitySummary;  // e.g., "UEs: Gauss-Markov 3D (0.3-0.8 m/s)"
    std::string trafficSummary;   // e.g., "HTTP/HTTPS/Video/VoIP mix"
    std::string notes;            // any extra remarks (buildings, traces, etc.)

    uint32_t ueCount = 0;
    uint32_t gnbCount = 0;
    uint32_t enbCount = 0;
    uint32_t meshApCount = 0;
    uint32_t staCount = 0;
};

struct ReportRow
{
    std::string idLabel;
    std::string trafficLabel;
    uint64_t txPackets = 0;
    uint64_t rxPackets = 0;
    uint64_t txBytes = 0;
    uint64_t rxBytes = 0;
    double pdrPercent = 0.0;
    double avgDelayMs = 0.0;
    double throughputMbps = 0.0;
};

struct ReportSummary
{
    double avgPdrPercent = 0.0;
    double avgDelayMs = 0.0;
    double avgThroughputMbps = 0.0;
    uint32_t measuredCount = 0;
};

ReportSummary WriteSimulationReport(const SimulationMetadata& metadata,
                                    const std::vector<ReportRow>& rows,
                                    double simulationTimeSeconds,
                                    std::ostream& consoleStream,
                                    std::ostream* fileStream = nullptr);

#endif  // REPORT_UTILS_H


