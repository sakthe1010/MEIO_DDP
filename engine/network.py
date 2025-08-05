class Network:
    def __init__(self, edges):
        self.upstream = {}
        self.downstream = {}
        for parent, child in edges:
            self.downstream.setdefault(parent, []).append(child)
            self.upstream.setdefault(child, []).append(parent)

    def get_upstream(self, node_name):
        return self.upstream.get(node_name, [])

    def get_downstream(self, node_name):
        return self.downstream.get(node_name, [])
