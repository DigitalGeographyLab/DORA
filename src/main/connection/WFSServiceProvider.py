import json
import time

from owslib.util import openURL

from src.main.connection import AbstractGeojsonProvider
from src.main.logic.Operations import Operations
from src.main.util import FileActions, getFormattedDatetime, timeDifference, Logger


class WFSServiceProvider(AbstractGeojsonProvider):
    def __init__(self, wfs_url="http://localhost:9000/geoserver/wfs?",
                 nearestVertexTypeName="", nearestRoutingVertexTypeName="",
                 shortestPathTypeName="", outputFormat="", epsgCode="EPSG:3857"):
        self.shortestPathTypeName = shortestPathTypeName
        self.__geoJson = None
        self.wfs_url = wfs_url
        self.nearestVertexTypeName = nearestVertexTypeName
        self.nearestRoutingVertexTypeName = nearestRoutingVertexTypeName
        self.outputFormat = outputFormat
        self.epsgCode = epsgCode
        self.operations = Operations(FileActions())

    # def getGeoJson(self):
    #     return self.__geoJson
    #
    # def setGeoJson(self, geojson):
    #     self.__geoJson = geojson
    def execute(self, url):
        """
        Request a JSON from an URL.

        :param url: URL.
        :return: Downloaded Json.
        """
        startTime = time.time()
        Logger.getInstance().info("requestFeatures Start Time: %s" % getFormattedDatetime(timemilis=startTime))

        u = openURL(url)

        geojson = json.loads(u.read().decode('utf-8'))

        endTime = time.time()
        Logger.getInstance().info("requestFeatures End Time: %s" % getFormattedDatetime(timemilis=endTime))

        totalTime = timeDifference(startTime, endTime)
        Logger.getInstance().info("requestFeatures Total Time: %s m" % totalTime)

        return geojson

    def getNearestVertexFromAPoint(self, coordinates):
        """
        From the WFS Service retrieve the nearest vertex from a given point coordinates.

        :param coordinates: Point coordinates. e.g [889213124.3123, 231234.2341]
        :return: Geojson (Geometry type: Point) with the nearest point coordinates.
        """
        coordinates = self.operations.transformPoint(coordinates, self.epsgCode)

        url = self.wfs_url + "service=WFS&version=1.0.0&request=GetFeature&typeName=%s&outputformat=%s&viewparams=x:%s;y:%s" % (
            self.nearestVertexTypeName, self.outputFormat, str(
                coordinates.getLongitude()), str(coordinates.getLatitude()))

        return self.execute(url)

    def getNearestRoutableVertexFromAPoint(self, coordinates):
        """
        From the WFS Service retrieve the nearest routing vertex from a given point coordinates.

        :param coordinates: Point coordinates. e.g [889213124.3123, 231234.2341]
        :return: Geojson (Geometry type: Point) with the nearest point coordinates.
        """
        url = self.wfs_url + "service=WFS&version=1.0.0&request=GetFeature&typeName=%s&outputformat=%s&viewparams=x:%s;y:%s" % (
            self.nearestRoutingVertexTypeName, self.outputFormat, str(
                coordinates.getLongitude()), str(coordinates.getLatitude()))

        return self.execute(url)

    def getShortestPath(self, startVertexId, endVertexId, cost):
        """
        From a pair of vertices (startVertexId, endVertexId) and based on the "cost" attribute,
        retrieve the shortest path by calling the WFS Service.

        :param startVertexId: Start vertex from the requested path.
        :param endVertexId: End vertex from the requested path.
        :param cost: Attribute to calculate the cost of the shortest path
        :return: Geojson (Geometry type: LineString) containing the segment features of the shortest path.
        """
        url = self.wfs_url + "service=WFS&version=1.0.0&request=GetFeature&typeName=%s&outputformat=%s&viewparams=source:%s;target:%s;cost:%s" % (
            self.shortestPathTypeName, self.outputFormat,
            startVertexId, endVertexId, cost)

        return self.execute(url)

    def getEPSGCode(self):
        return self.epsgCode
