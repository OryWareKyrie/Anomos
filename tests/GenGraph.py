#!/usr/bin/env python

import Anomos
import math
import os
import random
import string
import sys
from M2Crypto import X509
from Anomos import NetworkModel
import pygraphviz as pgv

class GenGraph(object):
    def __init__(self, p_reach=1):
        self.root = os.path.split(os.path.abspath(sys.argv[0]))[0]
        Anomos.Crypto.init(self.root)
        self.nm = NetworkModel.NetworkModel({'allow_close_neighbors':0})
        self.cert = X509.load_cert(os.path.join(Anomos.Crypto.global_cryptodir,"fake-peer-cert.pem"))
        self.p_reach=p_reach
        self.connect_order = []
    def init_peer(self, reachable=True):
        peerid = ''.join(str(i) for i in random.sample(string.lowercase, 20))
        ip = '.'.join(str(i) for i in random.sample(range(256),4))
        numcon = math.ceil(len(self.nm.reachable)**(1.0/3))
        self.nm.init_peer(peerid, self.cert, ip, '5881', 'session', numcon)
        self.connect_order.append(peerid)
        if reachable:
            # Make the peer reachable
            self.nm.get(peerid).nat = False
            self.nm.reachable.add(peerid)
    def degree_distribution(self):
        dd = {}
        for s in self.nm.names.values():
            x = len(s.neighbors)
            if dd.has_key(x):
                dd[x] += 1
            else:
                dd[x] = 1
        dds = dd.items()
        dds.sort()
        for i in dds:
            print "%d, %d" % i
    def announce(self, peerid):
        numcon = math.ceil(len(self.nm.reachable)**(1.0/3))
        s = self.nm.get(peerid)
        if s is not None:
            n = len(s.neighbors)
            if n < numcon:
                self.nm.rand_connect(s.name, numcon-n)
    def announce_all(self):
        map(self.announce, self.nm.names.values())
    def draw_graph(self, filename):
        G = pgv.AGraph()
        G.graph_attr.update(size="7")
        G.graph_attr.update(ratio="fill")
        G.graph_attr.update(ranksep=".5,1.0")

        G.node_attr.update(shape="circle")
        G.node_attr.update(fixedsize="True")
        G.node_attr.update(width="0.2")
        G.node_attr.update(height="0.2")
        G.node_attr.update(label="hax")
        G.node_attr.update(color="blue")
        G.add_nodes_from(self.nm.names, label="")
        for s in self.nm.names.values():
            if s.nat:
                G.get_node(s.name).attr['color']='orange'
            if len(s.neighbors) == 0:
                G.get_node(s.name).attr['color']='red'
            for n in s.neighbors:
                G.add_edge(s.name, n)

    # Layout options:
    # 1) Create fake center node, and connect all reachable peers to it
    # This structures the output such that reachable peers appear
    # clustered together in the center of the image
        #G.add_node("center", label="",style="invisible")
        #for n in self.nm.reachable:
        #    G.add_edge("center",n,style="invisible")
        #G.graph_attr.update(root="center")
    # 2) Choose the node with the fewest number of first and second degree
    # neighbors. This is roughly speaking the least connected peer in the network.
    # ... Sorry this is the worst code ever. It started as a simple list
    # comprehension and got steadily more complex ...
        center = min([
                        (len(s.neighbors) + sum([len(self.nm.get(i).neighbors)-1 for i in s.neighbors]), s)
                            for s in self.nm.names.values() if len(s.neighbors) > 0
                     ] or [(0, s)])[1]
        G.graph_attr.update(root=center.name)
        G.get_node(center.name).attr['style'] = 'filled'

        G.layout("twopi")
        G.draw(filename)

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print "USAGE: python %s ratio node_count" % sys.argv[0]
        print "\tratio - float, % of network which is reachable"
        print "\tnode_count - Total number of nodes in network"
        print "\tprefix - file will be output to ./graphs/prefix-ratio-node_count.png"
        sys.exit()
    ratio = float(sys.argv[1])
    size = int(sys.argv[2])
    prefix = sys.argv[3]
    gg = GenGraph(ratio)
    reachability = [1]*int(size*ratio)
    reachability.extend([0]*int(math.ceil(size*(1-ratio))))
    random.shuffle(reachability)
    arrival_rate = 5 # 1 every 5 minutes
    reannounce_interval = 45 # 1 every 45 minutes
    rst = reannounce_interval / arrival_rate
    counter = 0
    indx = 0
    for i in range(size):
        gg.init_peer(reachability[i])
        counter = (counter + 1) % rst
        if counter == 0:
            gg.announce(gg.connect_order[indx])
                    #TODO: uncomment when departure rate is added
            indx = (indx + 1) #% len(gg.connect_order)
    #gg.announce_all()
    #gg.announce_all()
    outdir = os.path.join(gg.root, "graphs")
    try:
        os.mkdir(outdir)
    except OSError:
        pass
    #gg.degree_distribution()
    gg.draw_graph(os.path.join(outdir,"%s-%.2f-%d.png" % (prefix, ratio, size)))



