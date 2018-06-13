class AbstractTransportMode:
    def getNearestVertexFromAPoint(self, coordinates):
        raise NotImplementedError("Should have implemented this")

    def getNearestRoutableVertexFromAPoint(self, coordinates, radius=500):
        raise NotImplementedError("Should have implemented this")

    def getShortestPath(self, startVertexId, endVertexId, cost):
        raise NotImplementedError("Should have implemented this")

    def getTotalShortestPathCostOneToOne(self, startVertexID, endVertexID, costAttribute):
        raise NotImplementedError("Should have implemented this")

    def getTotalShortestPathCostManyToOne(self, startVerticesID=[], endVertexID=None, costAttribute=None):
        raise NotImplementedError("Should have implemented this")

    def getTotalShortestPathCostOneToMany(self, startVertexID=None, endVerticesID=[], costAttribute=None):
        raise NotImplementedError("Should have implemented this")

    def getTotalShortestPathCostManyToMany(self, startVerticesID=[], endVerticesID=[], costAttribute=None):
        raise NotImplementedError("Should have implemented this")