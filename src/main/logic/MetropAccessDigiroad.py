import copy
import os

from joblib import delayed, Parallel

from src.main.carRoutingExceptions import NotURLDefinedException, \
    TransportModeNotDefinedException
from src.main.entities import Point
from src.main.logic.Operations import Operations
from src.main.reflection import Reflection
from src.main.util import GeometryType, getEnglishMeaning, FileActions, extractCRS, createPointFromPointFeature, \
    getConfigurationProperties, dgl_timer_enabled, \
    dgl_timer, parallel_job_print, Logger, PostfixAttribute, getFormattedDatetime, timeDifference

#from src.main.carRoutingExceptions import NotWFSDefinedException, NotURLDefinedException  # ONLY test purposes
from src.main.util import CostAttributes


# @dgl_timer
def createShortestPathFileWithAdditionalProperties(self,
                                                   costAttribute,
                                                   startPointFeature,
                                                   endPointFeature,
                                                   outputFolderPath,
                                                   summaryFolderPath,
                                                   csv_filename,
                                                   epsgCode,
                                                   endEpsgCode):
    # startTime = time.time()
    # functionName = "createShortestPathFileWithAdditionalProperties"
    # Logger.getInstance().info("%s Start Time: %s" % (functionName, getFormattedDatetime(timemilis=startTime)))

    ####################################
    startVertexId, newStartPointFeature = extractFeatureInformation(
        self=self,
        epsgCode=epsgCode,
        feature=startPointFeature,
        geojsonServiceProvider=self.transportMode,
        operations=self.operations
    )

    startCoordinates = newStartPointFeature["properties"]["selectedPointCoordinates"]
    startPoint = Point(latitute=startCoordinates[1],
                       longitude=startCoordinates[0],
                       epsgCode=self.transportMode.getEPSGCode())

    nearestStartCoordinates = newStartPointFeature["properties"]["nearestVertexCoordinates"]
    nearestStartPoint = Point(latitute=nearestStartCoordinates[1],
                              longitude=nearestStartCoordinates[0],
                              epsgCode=self.transportMode.getEPSGCode())
    ####################################
    endVertexId, newEndPointFeature = extractFeatureInformation(
        self=self,
        epsgCode=endEpsgCode,
        feature=endPointFeature,
        geojsonServiceProvider=self.transportMode,
        operations=self.operations
    )

    endCoordinates = newEndPointFeature["properties"]["selectedPointCoordinates"]
    endPoint = Point(latitute=endCoordinates[1],
                     longitude=endCoordinates[0],
                     epsgCode=self.transportMode.getEPSGCode())

    nearestEndCoordinates = newEndPointFeature["properties"]["nearestVertexCoordinates"]
    nearestEndPoint = Point(latitute=nearestEndCoordinates[1],
                            longitude=nearestEndCoordinates[0],
                            epsgCode=self.transportMode.getEPSGCode())
    ####################################

    if startPoint.equals(endPoint):
        return None, None, None, None

    # shortestPathId = str(startVertexId) + "_" + str(endVertexId)
    # existShortestPath = shortestPathId in self.shortestPathCache
    # if existShortestPath:
    #     shortestPath = self.shortestPathCache[shortestPathId]
    #     Logger.getInstance().info("Shortest path is cached %s " + shortestPathId)
    # else:
    #     shortestPath = self.transportMode.getShortestPath(startVertexId=startVertexId,
    #                                                       endVertexId=endVertexId,
    #                                                       cost=costAttribute)
    #     self.shortestPathCache[shortestPathId] = shortestPath

    # shortestPath = copy.deepcopy(shortestPath)
    ### The above cache procedure is too large that exceed the shared memory.

    shortestPath = self.transportMode.getShortestPath(startVertexId=startVertexId,
                                                      endVertexId=endVertexId,
                                                      cost=costAttribute)

    shortestPath["overallProperties"] = self.insertAdditionalProperties(
        newStartPointFeature,
        newEndPointFeature
    )

    shortestPath["overallProperties"]["selectedStartCoordinates"] = [startPoint.getLongitude(),
                                                                     startPoint.getLatitude()]
    shortestPath["overallProperties"]["selectedEndCoordinates"] = [endPoint.getLongitude(),
                                                                   endPoint.getLatitude()]
    shortestPath["overallProperties"]["nearestStartCoordinates"] = [nearestStartPoint.getLongitude(),
                                                                    nearestStartPoint.getLatitude()]
    shortestPath["overallProperties"]["nearestEndCoordinates"] = [nearestEndPoint.getLongitude(),
                                                                  nearestEndPoint.getLatitude()]

    shortestPath["overallProperties"]["startVertexId"] = startVertexId
    shortestPath["overallProperties"]["endVertexId"] = endVertexId

    if "totalFeatures" not in shortestPath:
        shortestPath["totalFeatures"] = len(shortestPath["features"])

    pointIdentifierKey = getConfigurationProperties(section="WFS_CONFIG")["point_identifier"]

    startPointIdentifier = newStartPointFeature["properties"][pointIdentifierKey]
    endPointIdentifier = newEndPointFeature["properties"][pointIdentifierKey]

    filename = "shortestPath"
    extension = "geojson"
    completeFilename = "%s-%s-%s-%s.%s" % (
        filename, getEnglishMeaning(costAttribute), startPointIdentifier, endPointIdentifier, extension)

    startPointId, endPointId, totalDistance, totalTravelTime = self.calculateSmallSummary(
        shortestPath=shortestPath,
        costAttribute=CostAttributes.BICYCLE_FAST_TIME
    )

    valueList = [startPointId, endPointId, totalDistance, totalTravelTime]
    self.fileActions.writeInCSV(summaryFolderPath, csv_filename, valueList)

    if "True".__eq__(getConfigurationProperties(section="WFS_CONFIG")["storeShortPathFile"]):
        self.fileActions.writeFile(folderPath=outputFolderPath, filename=completeFilename,
                                   data=shortestPath)

    # endTime = time.time()
    # Logger.getInstance().info("%s End Time: %s" % (functionName, getFormattedDatetime(timemilis=endTime)))
    #
    # totalTime = timeDifference(startTime, endTime)
    # Logger.getInstance().info("%s Total Time: %s m" % (functionName, totalTime))

    return outputFolderPath, completeFilename, summaryFolderPath, csv_filename


def extractFeatureInformation(self, epsgCode, feature, geojsonServiceProvider, operations):
    pointIdentifierKey = getConfigurationProperties(section="WFS_CONFIG")["point_identifier"]

    pointId = feature["properties"][pointIdentifierKey]
    if pointId in self.nearestVerticesCache:
        return self.nearestVerticesCache[pointId]

    coordinates = feature["geometry"]["coordinates"]
    featurePoint = Point(latitute=coordinates[1],
                         longitude=coordinates[0],
                         epsgCode=epsgCode)
    featurePoint = operations.transformPoint(featurePoint, geojsonServiceProvider.getEPSGCode())
    nearestVertexGeojson = geojsonServiceProvider.getNearestRoutableVertexFromAPoint(
        featurePoint)
    newFeaturePoint = nearestVertexGeojson["features"][0]
    vertexID = newFeaturePoint["properties"]["id"]
    feature["properties"]["vertex_id"] = vertexID
    ###
    epsgCodeNearestVertexCoordinates = extractCRS(nearestVertexGeojson)
    nearestPoint = createPointFromPointFeature(newFeaturePoint, epsgCodeNearestVertexCoordinates)
    nearestPoint = operations.transformPoint(nearestPoint, geojsonServiceProvider.getEPSGCode())
    ######## Add new properties to the start point feature
    feature["properties"]["selectedPointCoordinates"] = [featurePoint.getLongitude(),
                                                         featurePoint.getLatitude()]
    feature["properties"]["nearestVertexCoordinates"] = [nearestPoint.getLongitude(),
                                                         nearestPoint.getLatitude()]
    feature["properties"]["coordinatesCRS"] = featurePoint.getEPSGCode()
    ###

    self.nearestVerticesCache[pointId] = (vertexID, feature)

    return vertexID, feature


def createCostSummaryWithAdditionalProperties(self, costAttribute, startPointFeature, endPointFeature,
                                              costSummaryMap):
    startVertexID = startPointFeature["properties"]["vertex_id"]
    endVertexID = endPointFeature["properties"]["vertex_id"]

    # if startVertexID == endVertexID:
    #     return None
    if (startVertexID not in costSummaryMap) or (endVertexID not in costSummaryMap[startVertexID]):
        Logger.getInstance().warning("Not contained into the costSummaryMap: %s %s" % (startVertexID, endVertexID))
        return None

    summaryFeature = costSummaryMap[startVertexID][endVertexID]
    summaryFeature = copy.deepcopy(summaryFeature)

    total_cost = summaryFeature["properties"]["total_cost"]

    del summaryFeature["properties"]["start_vertex_id"]
    del summaryFeature["properties"]["end_vertex_id"]
    del summaryFeature["properties"]["total_cost"]

    # pointIdentifierKey = getConfigurationProperties(section="WFS_CONFIG")["point_identifier"]

    # startPointId = startPointFeature["properties"][pointIdentifierKey]
    # endPointId = endPointFeature["properties"][pointIdentifierKey]

    # newPropertiesId = startPointId + "-" + endPointId
    # if newPropertiesId in self.additionalFeaturePropertiesCache:
    #     newProperties = self.additionalFeaturePropertiesCache[newPropertiesId]
    # else:
    newProperties = self.insertAdditionalProperties(
        startPointFeature,
        endPointFeature
    )
    # self.additionalFeaturePropertiesCache[newPropertiesId] = newProperties

    # coordinates = summaryFeature["geometry"]["coordinates"]
    # coordinates[0] = startPointFeature["properties"]["selectedPointCoordinates"]
    # coordinates[1] = endPointFeature["properties"]["selectedPointCoordinates"]

    newProperties["costAttribute"] = getEnglishMeaning(costAttribute)
    newProperties[getEnglishMeaning(costAttribute)] = total_cost
    newProperties["startVertexId"] = startVertexID
    newProperties["endVertexId"] = endVertexID
    newProperties["selectedStartCoordinates"] = startPointFeature["properties"]["selectedPointCoordinates"]
    newProperties["selectedEndCoordinates"] = endPointFeature["properties"]["selectedPointCoordinates"]
    newProperties["nearestStartCoordinates"] = startPointFeature["properties"]["nearestVertexCoordinates"]
    newProperties["nearestEndCoordinates"] = endPointFeature["properties"]["nearestVertexCoordinates"]
    for key in newProperties:
        summaryFeature["properties"][key] = newProperties[key]

    return summaryFeature


class MetropAccessDigiroadApplication:
    def __init__(self, transportMode=None):
        self.fileActions = FileActions()
        self.operations = Operations(FileActions())
        self.reflection = Reflection()
        self.transportMode = transportMode
        self.nearestVerticesCache = {}
        self.additionalStartFeaturePropertiesCache = {}
        self.additionalEndFeaturePropertiesCache = {}
        self.shortestPathCache = {}

    @dgl_timer_enabled
    def calculateTotalTimeTravel(self,
                                 startCoordinatesGeojsonFilename=None,
                                 endCoordinatesGeojsonFilename=None,
                                 outputFolderPath=None,
                                 costAttribute=None):
        """
        Given a set of pair points and the ``cost attribute``, calculate the shortest path between each of them and
        store the Shortest Path Geojson file in the ``outputFolderPath``.

        :param wfsServiceProvider: WFS Service Provider data connection
        :param startCoordinatesGeojsonFilename: Geojson file (Geometry type: MultiPoint) containing pair of points.
        :param outputFolderPath: URL to store the shortest path geojson features of each pair of points.
        :param costAttribute: Attribute to calculate the impedance of the Shortest Path algorithm.
        :return: None. Store the information in the ``outputFolderPath``.
        """

        if not self.transportMode:
            raise TransportModeNotDefinedException()
        if not startCoordinatesGeojsonFilename or not outputFolderPath:
            raise NotURLDefinedException()

        if not outputFolderPath.endswith(os.sep):
            summaryFolderPath = outputFolderPath + os.sep + "summary" + os.sep
        else:
            summaryFolderPath = outputFolderPath + "summary" + os.sep

        if isinstance(costAttribute, dict):
            for key in costAttribute:
                newOutputFolderPath = outputFolderPath + os.sep + "geoms" + os.sep + \
                                      getEnglishMeaning(costAttribute[key]) + os.sep
                csv_filename = os.path.basename(startCoordinatesGeojsonFilename) + "_" + os.path.basename(
                    endCoordinatesGeojsonFilename) + "_" + getEnglishMeaning(costAttribute[key]) + "_costSummary.csv"
                zipCSVFilename = getEnglishMeaning(costAttribute[key]) + "_summary_csv.zip"

                self.fileActions.deleteFolder(path=newOutputFolderPath)
                self.fileActions.deleteFile(summaryFolderPath, csv_filename)
                # self.fileActions.deleteFile(summaryFolderPath, zipCSVFilename)

        else:
            newOutputFolderPath = outputFolderPath + os.sep + "geoms" + os.sep + getEnglishMeaning(
                costAttribute) + os.sep
            csv_filename = os.path.basename(startCoordinatesGeojsonFilename) + "_" + os.path.basename(
                endCoordinatesGeojsonFilename) + "_" + getEnglishMeaning(
                costAttribute) + "_costSummary.csv"
            zipCSVFilename = getEnglishMeaning(costAttribute) + "_summary_csv.zip"

            self.fileActions.deleteFolder(path=newOutputFolderPath)
            self.fileActions.deleteFile(summaryFolderPath, csv_filename)
            # self.fileActions.deleteFile(summaryFolderPath, zipCSVFilename)

        inputStartCoordinates = self.operations.mergeAdditionalLayers(
            originalJsonURL=startCoordinatesGeojsonFilename,
            outputFolderPath=outputFolderPath
        )

        inputEndCoordinates = self.operations.mergeAdditionalLayers(
            originalJsonURL=endCoordinatesGeojsonFilename,
            outputFolderPath=outputFolderPath
        )

        epsgCode = self.operations.extractCRSWithGeopandas(
            startCoordinatesGeojsonFilename)  # extractCRS(inputStartCoordinates)
        enDEpsgCode = self.operations.extractCRSWithGeopandas(
            endCoordinatesGeojsonFilename)  # extractCRS(inputStartCoordinates)

        delayedShortedPathCalculations = []

        ################################################################################################################
        for startPointFeature in inputStartCoordinates["features"]:
            # nearestStartPoint, startPoint, startPointEPSGCode, startVertexId = self.featureDataCompilation(
            #     startPointFeature, startCoordinatesGeojsonFilename, epsgCode
            # )


            for endPointFeature in inputEndCoordinates["features"]:
                # nearestEndPoint, endPoint, endPointEPSGCode, endVertexId = self.featureDataCompilation(
                #     endPointFeature, endCoordinatesGeojsonFilename, epsgCode
                # )

                if isinstance(costAttribute, dict):
                    for key in costAttribute:
                        newOutputFolderPath = outputFolderPath + os.sep + "geoms" + os.sep + getEnglishMeaning(
                            costAttribute[key]) + os.sep
                        csv_filename = os.path.basename(startCoordinatesGeojsonFilename) + "_" + os.path.basename(
                            endCoordinatesGeojsonFilename) + "_" + getEnglishMeaning(
                            costAttribute[key]) + "_costSummary.csv"

                        # self.createShortestPathFileWithAdditionalProperties(costAttribute[key], startVertexId,
                        #                                                     endVertexId,
                        #                                                     startPoint, newStartPointFeature,
                        #                                                     endPoint,
                        #                                                     newEndPointFeature, nearestEndPoint,
                        #                                                     nearestStartPoint,
                        #                                                     newOutputFolderPath, summaryFolderPath,
                        #                                                     csv_filename)

                        delayedShortedPathCalculations.append(
                            delayed(createShortestPathFileWithAdditionalProperties)(
                                self, costAttribute[key],
                                startPointFeature, endPointFeature,
                                newOutputFolderPath, summaryFolderPath,
                                csv_filename,
                                epsgCode,
                                enDEpsgCode
                            )
                        )
                else:
                    csv_filename = os.path.basename(startCoordinatesGeojsonFilename) + "_" + os.path.basename(
                        endCoordinatesGeojsonFilename) + "_" + getEnglishMeaning(costAttribute) + "_costSummary.csv"

                    # self.createShortestPathFileWithAdditionalProperties(costAttribute, startVertexId, endVertexId,
                    #                                                     startPoint, newStartPointFeature, endPoint,
                    #                                                     newEndPointFeature, nearestEndPoint,
                    #                                                     nearestStartPoint,
                    #                                                     newOutputFolderPath, summaryFolderPath,
                    #                                                     csv_filename)

                    delayedShortedPathCalculations.append(
                        delayed(createShortestPathFileWithAdditionalProperties)(
                            self,
                            costAttribute,
                            startPointFeature, endPointFeature,
                            newOutputFolderPath, summaryFolderPath,
                            csv_filename,
                            epsgCode,
                            enDEpsgCode)
                    )

        ################################################################################################################

        with Parallel(n_jobs=int(getConfigurationProperties(section="PARALLELIZATION")["jobs"]),
                      backend="threading",
                      verbose=int(getConfigurationProperties(section="PARALLELIZATION")["verbose"])) as parallel:
            parallel._print = parallel_job_print
            returns = parallel(tuple(delayedShortedPathCalculations))

        if isinstance(costAttribute, dict):
            for key in costAttribute:
                csv_filename = os.path.basename(startCoordinatesGeojsonFilename) + "_" + os.path.basename(
                    endCoordinatesGeojsonFilename) + "_" + getEnglishMeaning(costAttribute[key]) + "_costSummary.csv"

                self.storeCSVFile(getEnglishMeaning(costAttribute[key]), outputFolderPath, csv_filename)
        else:
            csv_filename = os.path.basename(startCoordinatesGeojsonFilename) + "_" + os.path.basename(
                endCoordinatesGeojsonFilename) + "_" + getEnglishMeaning(costAttribute) + "_costSummary.csv"

            self.storeCSVFile(getEnglishMeaning(costAttribute), outputFolderPath, csv_filename)

    def storeCSVFile(self, costAttribute, outputFolderPath, csv_filename):
        if not outputFolderPath.endswith(os.sep):
            summaryFolderPath = outputFolderPath + os.sep + "summary" + os.sep
        else:
            summaryFolderPath = outputFolderPath + "summary" + os.sep

        self.fileActions.compressOutputFile(
            folderPath=summaryFolderPath,
            zip_filename=costAttribute + "_summary_csv.zip",
            filepath=summaryFolderPath + os.sep + csv_filename
        )

        debug = False
        if "debug" in getConfigurationProperties(section="WFS_CONFIG"):
            debug = "True".__eq__(getConfigurationProperties(section="WFS_CONFIG")["debug"])

        if not debug:
            # self.fileActions.deleteFile(folderPath=summaryFolderPath, filename=outputFilename + ".geojson")
            self.fileActions.deleteFile(folderPath=summaryFolderPath, filename=csv_filename)

    def insertAdditionalProperties(self, startPointFeature, endPointFeature):
        startFeatureProperties = {}
        endFeatureProperties = {}

        pointIdentifierKey = getConfigurationProperties(section="WFS_CONFIG")["point_identifier"]

        startPointId = startPointFeature["properties"][pointIdentifierKey]
        endPointId = endPointFeature["properties"][pointIdentifierKey]

        existStartFeaturePropertiesCache = startPointId in self.additionalStartFeaturePropertiesCache
        if existStartFeaturePropertiesCache:
            startFeatureProperties = self.additionalStartFeaturePropertiesCache[startPointId]

        existEndFeaturePropertiesCache = endPointId in self.additionalEndFeaturePropertiesCache
        if existEndFeaturePropertiesCache:
            endFeatureProperties = self.additionalEndFeaturePropertiesCache[endPointId]


            # self.additionalFeaturePropertiesCache[newPropertiesId] = newProperties
        if (not existStartFeaturePropertiesCache) or (not existEndFeaturePropertiesCache):
            additionalLayerOperationLinkedList = self.reflection.getLinkedAbstractAdditionalLayerOperation()
            while additionalLayerOperationLinkedList.hasNext():
                additionalLayerOperation = additionalLayerOperationLinkedList.next()

                if not existStartFeaturePropertiesCache:
                    newPropertiesStartPointFeature = additionalLayerOperation.runOperation(
                        featureJson=startPointFeature,
                        prefix="startPoint_")
                    # for property in newPropertiesStartPointFeature:
                    #     startPointFeature["properties"][property] = newPropertiesStartPointFeature[property]
                    #     featureProperties[property] = newPropertiesStartPointFeature[property]
                    startFeatureProperties.update(newPropertiesStartPointFeature)

                if not existEndFeaturePropertiesCache:
                    newPropertiesEndPointFeature = additionalLayerOperation.runOperation(
                        featureJson=endPointFeature,
                        prefix="endPoint_")
                    # for property in newPropertiesEndPointFeature:
                    #     endPointFeature["properties"][property] = newPropertiesEndPointFeature[property]
                    #     featureProperties[property] = newPropertiesEndPointFeature[property]
                    endFeatureProperties.update(newPropertiesEndPointFeature)

        if not existStartFeaturePropertiesCache:
            self.additionalStartFeaturePropertiesCache[startPointId] = copy.deepcopy(startFeatureProperties)

        if not existEndFeaturePropertiesCache:
            self.additionalEndFeaturePropertiesCache[endPointId] = copy.deepcopy(endFeatureProperties)

        # featureProperties = {}
        # if existStartFeaturePropertiesCache:
        #     startFeatureProperties.update(endFeatureProperties)
        #     featureProperties = startFeatureProperties
        # elif existEndFeaturePropertiesCache:
        #     endFeatureProperties.update(startFeatureProperties)
        #     featureProperties = endFeatureProperties
        # else:
        startFeatureProperties.update(endFeatureProperties)
        featureProperties = startFeatureProperties

        return featureProperties

    @dgl_timer_enabled
    def createDetailedSummary(self, folderPath, costAttribute, outputFilename):
        """
        Given a set of Geojson (Geometry type: LineString) files, read all the files from the given ``folderPath`` and
        sum all the attribute values (distance, speed_limit_time, day_avg_delay_time, midday_delay_time and
        rush_hour_delay_time) and create a simple features Geojson (Geometry type: LineString)
        with the summary information.

        :param folderPath: Folder containing the shortest path geojson features.
        :param outputFilename: Filename to give to the summary file.
        :return: None. Store the summary information in the folderPath with the name given in outputFilename.
        """
        Logger.getInstance().info("Start createDetailedSummary for: %s" % costAttribute)

        if not folderPath.endswith(os.sep):
            attributeFolderPath = folderPath + os.sep + "geoms" + os.sep + getEnglishMeaning(costAttribute) + os.sep
            summaryFolderPath = folderPath + os.sep + "summary" + os.sep
        else:
            attributeFolderPath = folderPath + "geoms" + os.sep + getEnglishMeaning(costAttribute) + os.sep
            summaryFolderPath = folderPath + "summary" + os.sep

        totals = {
            "features": [],
            "totalFeatures": 0,
            "type": "FeatureCollection"
        }
        for file in os.listdir(attributeFolderPath):
            if file.endswith(".geojson") and file != "metroAccessDigiroadSummary.geojson":

                filemetadata = file.split("-")
                if len(filemetadata) < 2:
                    Logger.getInstance().info(filemetadata)

                shortestPath = self.fileActions.readJson(url=attributeFolderPath + file)

                if "crs" not in totals:
                    totals["crs"] = shortestPath["crs"]

                newSummaryFeature = {
                    "geometry": {
                        "coordinates": [
                        ],
                        "type": GeometryType.LINE_STRING
                    },
                    "properties": {
                        # "startVertexId": int(filemetadata[2]),
                        # "endVertexId": int(filemetadata[3].replace(".geojson", "")),
                        "costAttribute": filemetadata[1]
                    }
                }

                for property in shortestPath["overallProperties"]:
                    newSummaryFeature["properties"][property] = shortestPath["overallProperties"][property]

                startPoints = None
                endPoints = None
                lastSequence = 1

                for segmentFeature in shortestPath["features"]:
                    for key in segmentFeature["properties"]:
                        if key == "seq":
                            if segmentFeature["properties"][key] == 1:
                                # Sequence one is the first linestring geometry in the path
                                startPoints = segmentFeature["geometry"]["coordinates"]
                            if segmentFeature["properties"][key] > lastSequence:
                                # The last sequence is the last linestring geometry in the path
                                endPoints = segmentFeature["geometry"]["coordinates"]
                                lastSequence = segmentFeature["properties"][key]

                        if key not in ["id", "direction", "seq"]:
                            if key not in newSummaryFeature["properties"]:
                                newSummaryFeature["properties"][key] = 0

                            newSummaryFeature["properties"][key] = newSummaryFeature["properties"][key] + \
                                                                   segmentFeature["properties"][key]

                try:
                    newSummaryFeature["geometry"]["coordinates"] = newSummaryFeature["geometry"]["coordinates"] + \
                                                                   startPoints

                    startAndEndPointAreDifferent = lastSequence > 1
                    if startAndEndPointAreDifferent:
                        newSummaryFeature["geometry"]["coordinates"] = newSummaryFeature["geometry"]["coordinates"] + \
                                                                       endPoints
                    totals["features"].append(newSummaryFeature)
                except Exception as err:
                    Logger.getInstance().exception(err)
                    raise err

        totals["totalFeatures"] = len(totals["features"])
        outputFilename = getEnglishMeaning(costAttribute) + "_" + outputFilename
        self.fileActions.writeFile(folderPath=summaryFolderPath, filename=outputFilename, data=totals)

    @dgl_timer
    def calculateSmallSummary(self, shortestPath, costAttribute):
        """
        Given a Geojson (Geometry type: LineString) files, read all the files from the given ``folderPath`` and
        sum cost attribute and distance values (distance, and any of: speed_limit_time, day_avg_delay_time, midday_delay_time and
        rush_hour_delay_time) and return the sum up of those values.

        :param shortestPath: Shortest path geojson features.
        :param costAttribute: The sum up will be based on the given cost impedance value.
        :return: start point centroid id, end point centroid id, total distance and total travel time.
        """

        Logger.getInstance().info("Start calculateSmallSummary for: %s" % costAttribute)

        pointIdentifierKey = getConfigurationProperties(section="WFS_CONFIG")["point_identifier"]

        startPointId = shortestPath["overallProperties"]["startPoint_" + pointIdentifierKey]
        endPointId = shortestPath["overallProperties"]["endPoint_" + pointIdentifierKey]

        travelTime = 0.0
        distance = 0.0
        for segmentFeature in shortestPath["features"]:
            for key in segmentFeature["properties"]:
                if costAttribute == key:
                    travelTime += segmentFeature["properties"][costAttribute]
                if getEnglishMeaning(CostAttributes.DISTANCE) == key:
                    distance += segmentFeature["properties"][getEnglishMeaning(CostAttributes.DISTANCE)]

        totalDistance = shortestPath["overallProperties"]["startPoint_" + PostfixAttribute.EUCLIDEAN_DISTANCE] + \
                          shortestPath["overallProperties"]["startPoint_" + PostfixAttribute.AVG_WALKING_DISTANCE] + \
                          distance + \
                          shortestPath["overallProperties"]["endPoint_" + PostfixAttribute.AVG_WALKING_DISTANCE] + \
                          shortestPath["overallProperties"]["endPoint_" + PostfixAttribute.EUCLIDEAN_DISTANCE]

        totalTravelTime = shortestPath["overallProperties"]["startPoint_" + PostfixAttribute.EUCLIDEAN_DISTANCE + PostfixAttribute.WALKING_TIME] + \
                          shortestPath["overallProperties"]["startPoint_" + PostfixAttribute.AVG_WALKING_DISTANCE + PostfixAttribute.WALKING_TIME] + \
                          travelTime + \
                          shortestPath["overallProperties"]["endPoint_" + PostfixAttribute.PARKING_TIME] + \
                          shortestPath["overallProperties"]["endPoint_" + PostfixAttribute.AVG_WALKING_DISTANCE + PostfixAttribute.WALKING_TIME] + \
                          shortestPath["overallProperties"]["endPoint_" + PostfixAttribute.EUCLIDEAN_DISTANCE + PostfixAttribute.WALKING_TIME]

        return startPointId, endPointId, totalDistance, totalTravelTime

    @dgl_timer_enabled
    def createGeneralSummary(self, startCoordinatesGeojsonFilename, endCoordinatesGeojsonFilename, costAttribute,
                             outputFolderPath, outputFilename):
        """
        Using the power of pgr_Dijsktra algorithm this function calculate the total routing cost for a pair of set of points.
        It differentiate if must to use one-to-one, one-to-many, many-to-one or many-to-many specific stored procedures from the pgrouting extension.

        :param startCoordinatesGeojsonFilename: Geojson file (Geometry type: MultiPoint) containing pair of points.
        :param outputFolderPath: URL to store the shortest path geojson features of each pair of points.
        :param costAttribute: Attribute to calculate the impedance of the Shortest Path algorithm.
        :param outputFolderPath: Folder containing the shortest path geojson features.
        :param outputFilename: Filename to give to the summary file.
        :return: None. Store the information in the ``outputFolderPath``.
        """
        Logger.getInstance().info("Start createGeneralSummary for: %s" % costAttribute)

        Logger.getInstance().info("Start merge additional layers")
        inputStartCoordinates = self.operations.mergeAdditionalLayers(
            originalJsonURL=startCoordinatesGeojsonFilename,
            outputFolderPath=outputFolderPath
        )

        inputEndCoordinates = self.operations.mergeAdditionalLayers(
            originalJsonURL=endCoordinatesGeojsonFilename,
            outputFolderPath=outputFolderPath
        )
        Logger.getInstance().info("End merge additional layers")

        Logger.getInstance().info("Start nearest vertices finding")
        epsgCode = self.operations.extractCRSWithGeopandas(startCoordinatesGeojsonFilename)
        endEpsgCode = self.operations.extractCRSWithGeopandas(endCoordinatesGeojsonFilename)
        startVerticesID, startPointsFeaturesList = self.getVerticesID(inputStartCoordinates, epsgCode)
        endVerticesID, endPointsFeaturesList = self.getVerticesID(inputEndCoordinates, endEpsgCode)
        Logger.getInstance().info("End nearest vertices finding")

        totals = None

        Logger.getInstance().info("Start cost summary calculation")
        if len(startVerticesID) == 1 and len(endVerticesID) == 1:
            totals = self.transportMode.getTotalShortestPathCostOneToOne(
                startVertexID=startVerticesID[0],
                endVertexID=endVerticesID[0],
                costAttribute=costAttribute
            )
        elif len(startVerticesID) == 1 and len(endVerticesID) > 1:
            totals = self.transportMode.getTotalShortestPathCostOneToMany(
                startVertexID=startVerticesID[0],
                endVerticesID=endVerticesID,
                costAttribute=costAttribute
            )
        elif len(startVerticesID) > 1 and len(endVerticesID) == 1:
            totals = self.transportMode.getTotalShortestPathCostManyToOne(
                startVerticesID=startVerticesID,
                endVertexID=endVerticesID[0],
                costAttribute=costAttribute
            )
        elif len(startVerticesID) > 1 and len(endVerticesID) > 1:
            totals = self.transportMode.getTotalShortestPathCostManyToMany(
                startVerticesID=startVerticesID,
                endVerticesID=endVerticesID,
                costAttribute=costAttribute
            )
        Logger.getInstance().info("End cost summary calculation")

        costSummaryMap = self.createCostSummaryMap(totals)
        # summaryFeature = costSummaryMap[startVertexID][endVertexID]
        # KeyError: 125736

        counterStartPoints = 0
        counterEndPoints = 0

        ################################################################################################################
        # for featureShortPathSummary in totals["features"]:
        #     startVertexID = featureShortPathSummary["properties"]["start_vertex_id"]
        #     endVertexID = featureShortPathSummary["properties"]["end_vertex_id"]
        #     total_cost = featureShortPathSummary["properties"]["total_cost"]
        #     del featureShortPathSummary["properties"]["start_vertex_id"]
        #     del featureShortPathSummary["properties"]["end_vertex_id"]
        #     del featureShortPathSummary["properties"]["total_cost"]
        #
        #     startPointFeature = startPointsFeaturesList[counterStartPoints]
        #     endPointFeature = endPointsFeaturesList[counterEndPoints]
        #
        #     self.createCostSummaryWithAdditionalProperties(costAttribute, endPointFeature, endVertexID,
        #                                                    featureShortPathSummary, startPointFeature,
        #                                                    startVertexID,
        #                                                    total_cost)
        #     counterEndPoints += 1
        #     if counterEndPoints == len(endPointsFeaturesList):
        #         counterStartPoints += 1
        #         counterEndPoints = 0
        ################################################################################################################



        features = []
        ################################################################################################################
        # for startPointFeature in startPointsFeaturesList:
        #     for endPointFeature in endPointsFeaturesList:
        #         newFeature = createCostSummaryWithAdditionalProperties(costAttribute,
        #                                                                     startPointFeature,
        #                                                                     endPointFeature,
        #                                                                     costSummaryMap)
        #         if newFeature:
        #             features.append(newFeature)
        ################################################################################################################

        Logger.getInstance().info("Start createCostSummaryWithAdditionalProperties")
        with Parallel(n_jobs=int(getConfigurationProperties(section="PARALLELIZATION")["jobs"]),
                      backend="threading",
                      verbose=int(getConfigurationProperties(section="PARALLELIZATION")["verbose"])) as parallel:
            # while len(verticesID) <= len(geojson["features"]):
            parallel._print = parallel_job_print
            returns = parallel(delayed(createCostSummaryWithAdditionalProperties)(self,
                                                                                  costAttribute,
                                                                                  copy.deepcopy(startPointFeature),
                                                                                  copy.deepcopy(endPointFeature),
                                                                                  costSummaryMap)
                               for startPointFeature in startPointsFeaturesList
                               for endPointFeature in endPointsFeaturesList)

            for newFeature in returns:
                if newFeature:
                    features.append(newFeature)
                    # print(returns)

        Logger.getInstance().info("End createCostSummaryWithAdditionalProperties")

        ################################################################################################################

        totals["features"] = features
        if not outputFolderPath.endswith(os.sep):
            summaryFolderPath = outputFolderPath + os.sep + "summary" + os.sep
        else:
            summaryFolderPath = outputFolderPath + "summary" + os.sep

        pointIdentifierKey = getConfigurationProperties(section="WFS_CONFIG")["point_identifier"]
        columns = {
            "startPoint_" + pointIdentifierKey: "ykr_from_id",
            "endPoint_" + pointIdentifierKey: "ykr_to_id",
            "total_travel_time": "travel_time"
        }


        filepath = self.fileActions.writeFile(folderPath=summaryFolderPath, filename=outputFilename + ".geojson",
                                              data=totals)
        del totals

        dataframeSummary = self.operations.calculateTravelTimeFromGeojsonFile(
            travelTimeSummaryURL=filepath
        )

        dataframeSummary = self.operations.renameColumnsAndExtractSubSet(
            travelTimeMatrix=dataframeSummary,
            columns=columns
        )

        outputFilename = getEnglishMeaning(costAttribute) + "_" + outputFilename

        csv_separator = getConfigurationProperties(section="WFS_CONFIG")["csv_separator"]
        csv_path = os.path.join(summaryFolderPath, outputFilename + ".csv")

        if not os.path.exists(summaryFolderPath):
            os.makedirs(summaryFolderPath)

        dataframeSummary.to_csv(csv_path, sep=csv_separator, index=False)

        self.fileActions.compressOutputFile(
            folderPath=summaryFolderPath,
            zip_filename="summary.zip",
            filepath=filepath
        )

        self.fileActions.compressOutputFile(
            folderPath=summaryFolderPath,
            zip_filename="summary_csv.zip",
            filepath=csv_path
        )

        debug = False
        if "debug" in getConfigurationProperties(section="WFS_CONFIG"):
            debug = "True".__eq__(getConfigurationProperties(section="WFS_CONFIG")["debug"])

        if not debug:
            self.fileActions.deleteFile(folderPath=summaryFolderPath, filename=outputFilename + ".geojson")
            self.fileActions.deleteFile(folderPath=summaryFolderPath, filename=outputFilename + ".csv")

    @dgl_timer
    def getVerticesID(self, geojson, endEPSGCode):

        verticesID = []
        features = []

        # for feature in geojson["features"]:
        #     vertexID, feature = self.extractFeatureInformation(endEPSGCode, feature)
        #
        #     verticesID.append(vertexID)
        #     features.append(feature)
        with Parallel(n_jobs=int(getConfigurationProperties(section="PARALLELIZATION")["jobs"]),
                      backend="threading",
                      verbose=int(getConfigurationProperties(section="PARALLELIZATION")["verbose"])) as parallel:
            # while len(verticesID) <= len(geojson["features"]):
            parallel._print = parallel_job_print
            returns = parallel(
                delayed(extractFeatureInformation)(self, endEPSGCode, feature, self.transportMode, self.operations)
                for feature in geojson["features"])
            for vertexID, feature in returns:
                verticesID.append(vertexID)
                features.append(feature)
                # print(returns)

        return verticesID, features

    @dgl_timer
    def createCostSummaryMap(self, totals):
        """

        :param totals:
        :return:
        """
        """
            {
                "startId1": {
                    endId1: {feature1},
                    endId2: {feature2}
                }
                "startId2": {
                    endId1: {feature3},
                    endId2: {feature4}
                }
            }
            
        """

        costSummaryMap = {}
        for featureShortPathSummary in totals["features"]:
            startVertexID = featureShortPathSummary["properties"]["start_vertex_id"]
            endVertexID = featureShortPathSummary["properties"]["end_vertex_id"]
            if startVertexID not in costSummaryMap:
                costSummaryMap[startVertexID] = {}

            startVertexMap = costSummaryMap[startVertexID]
            startVertexMap[endVertexID] = featureShortPathSummary

        return costSummaryMap
