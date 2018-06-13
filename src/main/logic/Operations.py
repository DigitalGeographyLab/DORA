import json
import os

import geopandas as gpd
import numpy as np
import nvector as nv
from pyproj import Proj, transform

from src.main.entities import Point
from src.main.util import getConfigurationProperties, GPD_CRS, dgl_timer, Logger


class Operations:
    def __init__(self, fileActions):
        self.fileActions = fileActions

    @dgl_timer
    def mergeAdditionalLayers(self, originalJsonURL, outputFolderPath):
        """
        Merge all the layers listed in the ./resources/configuration.properties with the original json that contains the
        selected points.

        :param originalJsonURL: Points of interest.
        :param outputFolderPath: Output folder to store the temporal files.
        :return: Merged layer in geojson format.
        """

        layerNames = getConfigurationProperties("GEOJSON_LAYERS")
        layerAttributes = getConfigurationProperties("GEOJSON_LAYERS_ATTRIBUTES")

        originalJson = self.fileActions.readJson(originalJsonURL)
        completeFilename = "mergedLayer.geojson"
        temporalPath = os.path.join(outputFolderPath, "temp")
        temporalLayer = temporalPath + os.sep + completeFilename
        self.fileActions.writeFile(folderPath=temporalPath,
                                   filename=completeFilename,
                                   data=originalJson)

        for layerName in layerNames:
            attributes = layerAttributes[layerName + "_attributes"].split(",")
            fields = tuple(attributes)
            mergedLayer = self.mergeWithinPointsDataWithPolygonsAttributes(
                temporalLayer,
                layerNames[layerName],
                *fields)

            self.fileActions.writeFile(folderPath=temporalPath,
                                       filename=completeFilename,
                                       data=mergedLayer)

        originalJson = self.fileActions.readJson(temporalLayer)
        self.fileActions.deleteFolder(temporalPath)

        return originalJson

    def mergeWithinPointsDataWithPolygonsAttributes(self, pointsURL, polygonsURL, *fields):
        """
        Merge the points with the polygons attributes that match with the *fields param.

        :param pointsURL: Points of interest.
        :param polygonsURL: Polygons with additional data.
        :param fields: Polygons attributes to be merged.
        :return: Merged layer in geojson format.
        """

        points = gpd.read_file(pointsURL)
        polygons = gpd.read_file(polygonsURL)

        # Defining the subset of attributes to be merged.
        attributes = list(fields)
        if "geometry" not in attributes:
            attributes.append("geometry")

        polygons = polygons[attributes]

        originalPointsCRS = points.crs
        points = points.to_crs(GPD_CRS.WGS_84)
        polygons = polygons.to_crs(GPD_CRS.WGS_84)

        pointsWithNewFields = gpd.sjoin(points, polygons, how="left")
        pointsWithNewFields = pointsWithNewFields.to_crs(originalPointsCRS)

        jsonResult = pointsWithNewFields.to_json()
        jsonResult = json.loads(jsonResult)
        for feature in jsonResult["features"]:
            if "index_right" in feature["properties"]:
                del feature["properties"]["index_right"]

        # Unfortunately, geopandas is not exporting the CRS from the GeoDataFrame to the Geojson.
        # Passing the CRS manually.
        # https://github.com/geopandas/geopandas/issues/412
        jsonPoints = self.fileActions.readJson(pointsURL)
        jsonResult["crs"] = jsonPoints["crs"]
        return jsonResult

    def calculateTime(self, distance, speed):
        """
        Simple calculate of time given the distance traveled and the known speed

        :param distance: distance traveled.
        :param speed: known speed.
        :return: time spent.
        """
        if not distance or not speed:
            return 0.0

        time = distance / speed
        return time

    def calculateEuclideanDistance(self, startPoint=Point, endPoint=Point):
        """
        Calculate the distances between two points in meters.

        :param startPoint: latitude and longitud of the first point, must contain the CRS in which is given the coordinates
        :param endPoint: latitude and longitud of the second point, must contain the CRS in which is given the coordinates
        :return: Euclidean distance between the two points in meters.
        """

        startPointTransformed = self.transformPoint(startPoint)
        endPointTransformed = self.transformPoint(endPoint)

        wgs84 = nv.FrameE(name='WGS84')
        point1 = wgs84.GeoPoint(latitude=startPointTransformed.getLatitude(),
                                longitude=startPointTransformed.getLongitude(),
                                degrees=True)
        point2 = wgs84.GeoPoint(latitude=endPointTransformed.getLatitude(),
                                longitude=endPointTransformed.getLongitude(),
                                degrees=True)
        ellipsoidalDistance, _azi1, _azi2 = point1.distance_and_azimuth(point2)
        p_12_E = point2.to_ecef_vector() - point1.to_ecef_vector()
        euclideanDistance = np.linalg.norm(p_12_E.pvector, axis=0)[0]

        return euclideanDistance

    def transformPoint(self, point, targetEPSGCode="epsg:4326"):
        """
        Coordinates Transform from one CRS to another CRS.

        :param point:
        :param targetEPSGCode:
        :return:
        """
        if point.getEPSGCode().lower() == targetEPSGCode.lower():
            return point

        inProj = Proj(init=point.getEPSGCode())
        outProj = Proj(init=targetEPSGCode)

        lng, lat = transform(inProj, outProj, point.getLongitude(), point.getLatitude())

        return Point(latitute=lat, longitude=lng, epsgCode=targetEPSGCode)

    def extractCRSWithGeopandas(self, url):
        pointsDF = gpd.read_file(url)
        return pointsDF.crs["init"]

    @dgl_timer
    def calculateTravelTimeFromGeojsonFile(self, travelTimeSummaryURL):
        travelTimeSummaryDF = gpd.GeoDataFrame.from_file(travelTimeSummaryURL)
        return self.calculateTravelTimeFromDataframe(travelTimeSummaryDF)

    @dgl_timer
    def calculateTravelTimeFromGeojsonObject(self, travelTimeSummary):
        if "features" in travelTimeSummary:
            travelTimeSummaryDF = self.fileActions.transformGeojsonInDataFrame(travelTimeSummary)
            return self.calculateTravelTimeFromDataframe(travelTimeSummaryDF)

    @dgl_timer
    def calculateTravelTimeFromDataframe(self, travelTimeSummaryDF):
        Logger.getInstance().info("Dataframe length=%s" % len(travelTimeSummaryDF))

        if len(travelTimeSummaryDF["costAttribute"]) > 0:
            costAttribute = travelTimeSummaryDF["costAttribute"][0]
            travelTimeSummaryDF["total_travel_time"] = travelTimeSummaryDF.startPoint_EuclideanDistanceWalkingTime + \
                                                       travelTimeSummaryDF.startPoint_AVGWalkingDistanceWalkingTime + \
                                                       travelTimeSummaryDF[costAttribute] + \
                                                       travelTimeSummaryDF.endPoint_ParkingTime + \
                                                       travelTimeSummaryDF.endPoint_AVGWalkingDistanceWalkingTime + \
                                                       travelTimeSummaryDF.endPoint_EuclideanDistanceWalkingTime

        return travelTimeSummaryDF

    @dgl_timer
    def renameColumnsAndExtractSubSet(self, travelTimeMatrix, columns, geometryColumn="geometry"):
        if columns:
            keys = [key for key in columns]

            # keys.append(geometryColumn) # the geometry is removed, it will be used the join with the grid centroid table

            travelTimeMatrix = travelTimeMatrix[keys]
            travelTimeMatrix = travelTimeMatrix.rename(index=str, columns=columns)
        return travelTimeMatrix
