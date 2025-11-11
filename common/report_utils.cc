#include "common/report_utils.h"

#include <algorithm>
#include <iomanip>
#include <numeric>
#include <sstream>

namespace
{
constexpr int kIdWidth = 10;
constexpr int kTrafficWidth = 20;
constexpr int kPdrWidth = 12;
constexpr int kDelayWidth = 14;
constexpr int kThroughputWidth = 18;
constexpr int kPacketWidth = 14;
constexpr int kBytesWidth = 18;

std::string
BuildSeparator()
{
    return std::string(92, '=');
}

void
EmitMetadata(std::ostream& os, const SimulationMetadata& metadata, double simulationTimeSeconds)
{
    const std::string separator = BuildSeparator();
    os << "\n" << separator << "\n";
    os << metadata.scenarioName << "\n";
    os << separator << "\n";
    if (!metadata.environment.empty())
    {
        os << "Environment   : " << metadata.environment << "\n";
    }
    if (!metadata.topologySummary.empty())
    {
        os << "Topology      : " << metadata.topologySummary << "\n";
    }
    os << "Node Counts   : ";
    bool first = true;
    auto emitCount = [&](const std::string& label, uint32_t value) {
        if (value == 0)
        {
            return;
        }
        if (!first)
        {
            os << ", ";
        }
        os << value << " " << label;
        first = false;
    };
    emitCount("UEs", metadata.ueCount);
    emitCount("gNBs", metadata.gnbCount);
    emitCount("eNBs", metadata.enbCount);
    emitCount("Mesh APs", metadata.meshApCount);
    emitCount("STAs", metadata.staCount);
    if (first)
    {
        os << "n/a";
    }
    os << "\n";
    if (!metadata.mobilitySummary.empty())
    {
        os << "Mobility      : " << metadata.mobilitySummary << "\n";
    }
    if (!metadata.trafficSummary.empty())
    {
        os << "Traffic Mix   : " << metadata.trafficSummary << "\n";
    }
    if (!metadata.notes.empty())
    {
        os << "Notes         : " << metadata.notes << "\n";
    }
    os << "Simulation    : " << std::fixed << std::setprecision(2) << simulationTimeSeconds << " s\n";
    os << separator << "\n";
}

void
EmitHeader(std::ostream& os)
{
    const std::string separator = BuildSeparator();
    os << std::left << std::setw(kIdWidth) << "ID"
       << std::setw(kTrafficWidth) << "Traffic"
       << std::right << std::setw(kPdrWidth) << "PDR (%)"
       << std::setw(kDelayWidth) << "Delay (ms)"
       << std::setw(kThroughputWidth) << "Throughput (Mbps)"
       << std::setw(kPacketWidth) << "TX Pkts"
       << std::setw(kPacketWidth) << "RX Pkts"
       << std::setw(kBytesWidth) << "RX Bytes"
       << "\n";
    os << separator << "\n";
}

void
EmitRows(std::ostream& os, const std::vector<ReportRow>& rows)
{
    for (const auto& row : rows)
    {
        os << std::left << std::setw(kIdWidth) << row.idLabel
           << std::setw(kTrafficWidth) << row.trafficLabel
           << std::right << std::fixed << std::setprecision(2)
           << std::setw(kPdrWidth) << row.pdrPercent
           << std::setw(kDelayWidth) << row.avgDelayMs
           << std::setw(kThroughputWidth) << row.throughputMbps
           << std::setw(kPacketWidth) << row.txPackets
           << std::setw(kPacketWidth) << row.rxPackets
           << std::setw(kBytesWidth) << row.rxBytes
           << "\n";
    }
}

void
EmitSummary(std::ostream& os, const ReportSummary& summary)
{
    const std::string separator = BuildSeparator();
    os << separator << "\n";
    os << "SUMMARY STATISTICS (" << summary.measuredCount << " entries)\n";
    os << "Average PDR        : " << std::fixed << std::setprecision(2) << summary.avgPdrPercent << " %\n";
    os << "Average Delay      : " << summary.avgDelayMs << " ms\n";
    os << "Average Throughput : " << summary.avgThroughputMbps << " Mbps\n";
    os << separator << "\n";
}

ReportSummary
ComputeSummary(const std::vector<ReportRow>& rows)
{
    ReportSummary summary{};
    uint32_t count = 0;
    double pdrSum = 0.0;
    double delaySum = 0.0;
    double throughputSum = 0.0;

    for (const auto& row : rows)
    {
        if (row.txPackets == 0)
        {
            continue;
        }
        pdrSum += row.pdrPercent;
        delaySum += row.avgDelayMs;
        throughputSum += row.throughputMbps;
        ++count;
    }

    summary.measuredCount = count;
    if (count > 0)
    {
        summary.avgPdrPercent = pdrSum / count;
        summary.avgDelayMs = delaySum / count;
        summary.avgThroughputMbps = throughputSum / count;
    }
    return summary;
}

void
EmitReport(std::ostream& os,
           const SimulationMetadata& metadata,
           const std::vector<ReportRow>& rows,
           double simulationTimeSeconds,
           const ReportSummary& summary)
{
    EmitMetadata(os, metadata, simulationTimeSeconds);
    EmitHeader(os);
    EmitRows(os, rows);
    EmitSummary(os, summary);
}
} // namespace

ReportSummary
WriteSimulationReport(const SimulationMetadata& metadata,
                      const std::vector<ReportRow>& rows,
                      double simulationTimeSeconds,
                      std::ostream& consoleStream,
                      std::ostream* fileStream)
{
    ReportSummary summary = ComputeSummary(rows);
    EmitReport(consoleStream, metadata, rows, simulationTimeSeconds, summary);

    if (fileStream != nullptr)
    {
        EmitReport(*fileStream, metadata, rows, simulationTimeSeconds, summary);
        fileStream->flush();
    }

    return summary;
}


