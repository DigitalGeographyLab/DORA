import os
import unittest

from src.main.carRoutingExceptions import IncorrectGeometryTypeException
from src.main.connection.WFSServiceProvider import WFSServiceProvider
from src.main.logic.Operations import Operations
from src.main.util import CostAttributes, FileActions

from src.main.entities import Point


class WFSServiceProviderTest(unittest.TestCase):
    def setUp(self):
        self.wfsServiceProvider = WFSServiceProvider(wfs_url="http://localhost:9000/geoserver/wfs?",
                                                     nearestVertexTypeName="tutorial:dgl_nearest_vertex",
                                                     nearestRoutingVertexTypeName="tutorial:dgl_nearest_car_routable_vertex",
                                                     shortestPathTypeName="tutorial:dgl_shortest_path",
                                                     outputFormat="application/json")
        self.fileActions = FileActions()
        self.operations = Operations(self.fileActions)
        self.dir = os.getcwd()

    def test_givenA_URL_then_returnJsonObject(self):
        dir = self.dir + '/src/test/data/geojson/testPoints.geojson'
        self.assertIsNotNone(self.fileActions.readMultiPointJson(dir))

    def test_givenAGeoJson_then_attributeDataMustExist(self):
        dir = self.dir + '/src/test/data/geojson/testPoints.geojson'
        multiPoints = self.fileActions.readMultiPointJson(dir)
        self.assertIsNotNone(multiPoints["features"])

    def test_givenAGeoJsonWithAttributeData_then_attributeFeaturesMustExist(self):
        dir = self.dir + '/src/test/data/geojson/testPoints.geojson'
        multiPoints = self.fileActions.readMultiPointJson(dir)
        self.assertIsNotNone(multiPoints["features"])

    def test_givenAGeoJsonWithPointData_then_FeaturesPointMustExist(self):
        dir = self.dir + '/src/test/data/geojson/reititinTestPoints.geojson'
        multiPoints = self.fileActions.readPointJson(dir)
        self.assertIsNotNone(multiPoints["features"])

    def test_givenAnEmptyGeoJson_then_allowed(self):
        dir = self.dir + '/src/test/data/geojson/testEmpty.geojson'
        multiPoints = self.fileActions.readMultiPointJson(dir)
        self.assertEquals(0, len(multiPoints["features"]))

    def test_eachFeatureMustBeMultiPointType_IfNot_then_throwNotMultiPointGeometryError(self):
        dir = self.dir + '/src/test/data/geojson/testNotMultiPointGeometry.geojson'
        self.assertRaises(IncorrectGeometryTypeException, self.fileActions.readMultiPointJson, dir)

    def test_givenAPairOfPoints_retrieveSomething(self):
        # point_coordinates = {
        #     "lat": 60.1836272547957,
        #     "lng": 24.929379456878265
        # }
        coordinates = Point(latitute=60.1836272547957,
                            longitude=24.929379456878265,
                            epsgCode="EPSG:4326")

        self.assertIsNotNone(self.wfsServiceProvider.getNearestRoutableVertexFromAPoint(coordinates))

    def test_givenAPoint_retrieveNearestCarRoutingVertexGeojson(self):
        # point_coordinates = {  # EPSG:3857
        #     "lat": 8443095.452975733,
        #     "lng": 2770620.87667954
        # }

        # coordinates = Point(latitute=8443095.452975733,
        #                     longitude=2770620.87667954,
        #                     epsgCode="EPSG:3857")

        coordinates = Point(latitute=6672380.0,
                            longitude=385875.0,
                            epsgCode="EPSG:3047")

        nearestVertexExpectedGeojson = self.readGeojsonExpectedResponse(
            '/src/test/data/geojson/nearestCarRoutingVertexResponseGeoServer.geojson')

        coordinates = self.operations.transformPoint(coordinates, self.wfsServiceProvider.getEPSGCode())

        geoJson = self.wfsServiceProvider.getNearestRoutableVertexFromAPoint(coordinates)

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

    def test_givenAPoint_retrieveNearestVertexGeojson(self):
        # point_coordinates = {  # EPSG:3857
        #     "lat": 8443095.452975733,
        #     "lng": 2770620.87667954
        # }

        coordinates = Point(latitute=8443095.452975733,
                            longitude=2770620.87667954,
                            epsgCode="EPSG:3857")

        nearestVertexExpectedGeojson = self.readGeojsonExpectedResponse(
            '/src/test/data/geojson/nearestVertextResponse.geojson')

        self.assertEqual(nearestVertexExpectedGeojson, self.wfsServiceProvider.getNearestVertexFromAPoint(coordinates))

    def test_givenAPairOfPoints_then_retrieveTheShortestPath(self):
        self.maxDiff = None

        shortestPathGeojson = self.readShortestPathGeojsonExpectedResponse()
        for feature in shortestPathGeojson["features"]:
            if "id" in feature:
                del feature["id"]
            if "geometry_name" in feature:
                del feature["geometry_name"]

        shortestPathResult = self.wfsServiceProvider.getShortestPath(startVertexId=106290, endVertexId=96275,
                                                                     cost=CostAttributes.DISTANCE)
        for feature in shortestPathResult["features"]:
            if "id" in feature:
                del feature["id"]
            if "geometry_name" in feature:
                del feature["geometry_name"]

        self.assertDictEqual(shortestPathGeojson,
                             shortestPathResult)

    def readGeojsonExpectedResponse(
            self,
            geojsonPath):

        fileDir = self.dir + geojsonPath
        nearestVertexGeojson = self.fileActions.readJson(fileDir)
        return nearestVertexGeojson

    def readShortestPathGeojsonExpectedResponse(self):
        fileDir = self.dir + '/src/test/data/geojson/shortestPathResponse.geojson'
        shortestPathGeojson = self.fileActions.readJson(fileDir)
        return shortestPathGeojson
