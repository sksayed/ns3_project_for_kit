import ns.applications
import ns.core
import ns.internet
import ns.mesh
import ns.mobility
import ns.network
import ns.yans 

def main():
    print('my first wifi simulation in ns3')

    number_of_nodes = 6

    # create nodes
    nodes = ns.network.NodeContainer()
    nodes.Create(number_of_nodes)

    mobilityHelper = ns.mobility.MobilityHelper()
    
    