import os
import unittest

from src.main.connection.WFSServiceProvider import WFSServiceProvider
from src.main.entities import Point
from src.main.logic.Operations import Operations
from src.main.util import FileActions, Logger


class OperationsTest(unittest.TestCase):
    def setUp(self):
        self.wfsServiceProvider = WFSServiceProvider(wfs_url="http://localhost:9000/geoserver/wfs?",
                                                     nearestVertexTypeName="tutorial:dgl_nearest_vertex",
                                                     nearestRoutingVertexTypeName="tutorial:dgl_nearest_car_routable_vertex",
                                                     shortestPathTypeName="tutorial:dgl_shortest_path",
                                                     outputFormat="application/json")
        self.fileActions = FileActions()
        self.operations = Operations(self.fileActions)

        self.dir = os.getcwd()

    def test_givenASetOfPointsAndASetOfPolygons_then_mergeAttributesFromThePolygonToThePointsWithinThePolygon(self):
        withinPointsURL = self.dir + '%src%test%data%geojson%withinPoints.geojson'.replace("%", os.sep)
        testPointsURL = self.dir + '%src%test%data%geojson%reititinTestPoints.geojson'.replace("%", os.sep)
        testPolygonsURL = self.dir + '%src%test%data%geojson%helsinki-regions.geojson'.replace("%", os.sep)

        expectedWithinPoints = self.fileActions.readJson(withinPointsURL)

        withinPoints = self.operations.mergeWithinPointsDataWithPolygonsAttributes(testPointsURL,
                                                                                   testPolygonsURL,
                                                                                   "walking_distance",
                                                                                   "parking_time")

        self.assertEqual(expectedWithinPoints, withinPoints)

    def test_givenASetOfPoints_then_mergeAllTheMergeableLayersWithTheOriginalPoints(self):
        expectedMergedLayerURL = self.dir + '%src%test%data%geojson%mergedLayerGeoServer.geojson'.replace("%", os.sep)
        testPointsURL = self.dir + '%src%test%data%geojson%reititinTestPoints.geojson'.replace("%", os.sep)
        outputFolderFeaturesURL = self.dir + '%src%test%data%outputFolder%'.replace("%", os.sep)

        mergedLayer = self.operations.mergeAdditionalLayers(originalJsonURL=testPointsURL,
                                                            outputFolderPath=outputFolderFeaturesURL)

        expectedMergedLayer = self.fileActions.readJson(expectedMergedLayerURL)
        self.assertEqual(expectedMergedLayer, mergedLayer)

    def test_calculateEuclideanDistanceToTheNearestVertex(self):
        euclideanDistanceExpected = 54.918796781644275  # 307.99402311696525  # meters
        startPoint = {
            "lat": 6672380.0,
            "lng": 385875.0,
            "crs": "EPSG:3047"
        }
        startPoint = Point(latitute=startPoint["lat"],
                           longitude=startPoint["lng"],
                           epsgCode="EPSG:3047")
        newStartPoint = self.operations.transformPoint(startPoint, targetEPSGCode=self.wfsServiceProvider.getEPSGCode())

        nearestVertex = self.wfsServiceProvider.getNearestRoutableVertexFromAPoint(newStartPoint)
        epsgCode = nearestVertex["crs"]["properties"]["name"].split(":")[-3] + ":" + \
                   nearestVertex["crs"]["properties"]["name"].split(":")[-1]

        # endPoint = {
        #     "lat": nearestVertex["features"][0]["geometry"]["coordinates"][0][1],
        #     "lng": nearestVertex["features"][0]["geometry"]["coordinates"][0][0],
        #     "crs": epsgCode
        # }

        endPoint = Point(latitute=nearestVertex["features"][0]["geometry"]["coordinates"][0][1],
                         longitude=nearestVertex["features"][0]["geometry"]["coordinates"][0][0],
                         epsgCode=epsgCode)

        self.assertEqual(euclideanDistanceExpected,
                         self.operations.calculateEuclideanDistance(newStartPoint, endPoint))

    def test_givenAPoint_retrieveEuclideanDistanceToTheNearestVertex(self):
        euclideanDistanceExpected = 1.4044170756169843  # meters
        # startPoint = {
        #     "lat": 8443095.452975733,
        #     "lng": 2770620.87667954,
        #     "crs": "EPSG:3857"
        # }
        startPoint = Point(latitute=8443095.452975733,
                           longitude=2770620.87667954,
                           epsgCode="EPSG:3857")

        nearestVertex = self.wfsServiceProvider.getNearestRoutableVertexFromAPoint(startPoint)
        epsgCode = nearestVertex["crs"]["properties"]["name"].split(":")[-3] + ":" + \
                   nearestVertex["crs"]["properties"]["name"].split(":")[-1]

        # endPoint = {
        #     "lat": nearestVertex["features"][0]["geometry"]["coordinates"][0][1],
        #     "lng": nearestVertex["features"][0]["geometry"]["coordinates"][0][0],
        #     "crs": epsgCode
        # }

        endPoint = Point(latitute=nearestVertex["features"][0]["geometry"]["coordinates"][0][1],
                         longitude=nearestVertex["features"][0]["geometry"]["coordinates"][0][0],
                         epsgCode=epsgCode)

        self.assertEqual(euclideanDistanceExpected,
                         self.operations.calculateEuclideanDistance(startPoint, endPoint))

    def test_transformPoint_to_newCoordinateSystem(self):
        url = self.dir + '%src%test%data%geojson%Subsets%1_Origs_WGS84.geojson'.replace("%", os.sep)
        epsgCode = self.operations.extractCRSWithGeopandas(url)
        # print(epsgCode)
        self.assertEqual("epsg:4326", epsgCode)

    def test_logger(self):
        outputFolder = self.dir + '%src%test%data%outputFolder'.replace("%", os.sep)

        Logger.configureLogger(outputFolder=outputFolder,
                               prefix="prefix")

        Logger.getInstance().info("MY LOG")
