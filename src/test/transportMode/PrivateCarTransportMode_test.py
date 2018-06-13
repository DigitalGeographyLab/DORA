import os
import unittest

from src.main.connection.PostgisServiceProvider import PostgisServiceProvider
from src.main.entities import Point
from src.main.logic.Operations import Operations
from src.main.util import CostAttributes, FileActions

from src.main.transportMode.PrivateCarTransportMode import PrivateCarTransportMode


class PrivateCarTransportModeTest(unittest.TestCase):
    def setUp(self):
        postgisServiceProvider = PostgisServiceProvider()
        self.privateCarTransportMode = PrivateCarTransportMode(postgisServiceProvider)
        self.fileActions = FileActions()
        self.operations = Operations(self.fileActions)
        self.dir = os.getcwd()

    def test_givenAPoint_retrieveNearestCarRoutingVertexGeojson(self):
        # point_coordinates = {  # EPSG:3857
        #     "lat": 8443095.452975733,
        #     "lng": 2770620.87667954
        # }
        vertexGeojsonURL = self.dir + '/src/test/data/geojson/nearestCarRoutingVertexResponse.geojson'
        nearestVertexExpectedGeojson = self.fileActions.readJson(vertexGeojsonURL)

        coordinates = Point(latitute=6672380.0,
                            longitude=385875.0,
                            epsgCode="EPSG:3047")

        coordinates = self.operations.transformPoint(coordinates, self.privateCarTransportMode.getEPSGCode())

        geoJson = self.privateCarTransportMode.getNearestRoutableVertexFromAPoint(coordinates)

        for feature in nearestVertexExpectedGeojson["features"]:
            if "id" in feature:
                del feature["id"]

        if "totalFeatures" in geoJson:
            del geoJson["totalFeatures"]

        for feature in geoJson["features"]:
            if "id" in feature:
                del feature["id"]
            if "geometry_name" in feature:
                del feature["geometry_name"]

        self.assertEqual(nearestVertexExpectedGeojson, geoJson)

    def test_givenAPairOfVertex_then_retrieveDijsktraOneToOneCostSummaryGeojson(self):
        dir = self.dir + '%src%test%data%geojson%oneToOneCostSummary.geojson'.replace("%", os.sep)

        expectedSummary = self.fileActions.readJson(dir)
        summaryShortestPathCostOneToOne = self.privateCarTransportMode.getTotalShortestPathCostOneToOne(
            startVertexID=59227,
            endVertexID=2692,
            costAttribute=CostAttributes.DISTANCE
        )
        self.assertEqual(expectedSummary, summaryShortestPathCostOneToOne)

    def test_givenASetOfVertexesVsOneVertex_then_retrieveDijsktraManyToOneCostSummaryGeojson(self):
        dir = self.dir + '%src%test%data%geojson%manyToOneCostSummary.geojson'.replace("%", os.sep)

        expectedSummary = self.fileActions.readJson(dir)
        summaryShortestPathCostManyToOne = self.privateCarTransportMode.getTotalShortestPathCostManyToOne(
            startVerticesID=[99080, 78618, 45174, 46020, 44823, 110372, 140220, 78317, 106993, 127209, 33861, 49020],
            endVertexID=99080,
            costAttribute=CostAttributes.DISTANCE
        )
        self.assertEqual(expectedSummary, summaryShortestPathCostManyToOne)

    def test_givenAVertexVsASetOfVertexes_then_retrieveDijsktraOneToManyCostSummaryGeojson(self):
        dir = self.dir + '%src%test%data%geojson%oneToManyCostSummary.geojson'.replace("%", os.sep)

        expectedSummary = self.fileActions.readJson(dir)
        summaryShortestPathCostOneToMany = self.privateCarTransportMode.getTotalShortestPathCostOneToMany(
            startVertexID=99080,
            endVerticesID=[99080, 78618, 45174, 46020, 44823, 110372, 140220, 78317, 106993, 127209, 33861, 49020],
            costAttribute=CostAttributes.DISTANCE
        )
        self.assertEqual(expectedSummary, summaryShortestPathCostOneToMany)

    def test_givenASetOfVertexesVsASetOfVertexes_then_retrieveDijsktraManyToManyCostSummaryGeojson(self):
        dir = self.dir + '%src%test%data%geojson%manyToManyCostSummary.geojson'.replace("%", os.sep)

        expectedSummary = self.fileActions.readJson(dir)
        summaryShortestPathCostManyToMany = self.privateCarTransportMode.getTotalShortestPathCostManyToMany(
            startVerticesID=[99080, 78618, 45174, 46020, 44823, 110372, 140220, 78317, 106993, 127209, 33861, 49020],
            endVerticesID=[99080, 78618, 45174, 46020, 44823, 110372, 140220, 78317, 106993, 127209, 33861, 49020],
            costAttribute=CostAttributes.DISTANCE
        )
        self.assertEqual(expectedSummary, summaryShortestPathCostManyToMany)

    def test_bucle(self):
        arrayList = [0, 1, 2, 3, 4, 5, 6, 7, 8]
        expected = [[0, 3], [4, 7], [8, 8]]

        jump = 4
        self.assertEqual(expected, self.getModules(arrayList, jump))

        arrayList = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        expected = [[0, 3], [4, 7], [8, 9]]

        self.assertEqual(expected, self.getModules(arrayList, jump))

        arrayList = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        expected = [[0, 3], [4, 7], [8, 10]]

        self.assertEqual(expected, self.getModules(arrayList, jump))

        arrayList = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        expected = [[0, 3], [4, 7], [8, 11]]

        self.assertEqual(expected, self.getModules(arrayList, jump))

        arrayList = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        expected = [[0, 3], [4, 7], [8, 11], [12, 12]]

        self.assertEqual(expected, self.getModules(arrayList, jump))

        arrayList = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        expected = [[0, 2], [3, 5], [6, 8], [9, 11], [12, 12]]
        jump = 3
        self.assertEqual(expected, self.getModules(arrayList, jump))

    def getModules(self, arrayList, jump):
        counter = 0
        intervals = []
        while counter < len(arrayList):
            if counter + jump > len(arrayList):
                jump = len(arrayList) % jump

            intervals.append([counter, counter + jump - 1])
            counter = counter + jump
        print(intervals)
        return intervals
