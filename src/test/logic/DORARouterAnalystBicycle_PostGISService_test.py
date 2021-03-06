import multiprocessing
import os
import unittest
from math import sqrt

from joblib import Parallel, delayed
from src.main.carRoutingExceptions import NotURLDefinedException, \
    TransportModeNotDefinedException
from src.main.connection.PostgisServiceProvider import PostgisServiceProvider
from src.main.logic.DORARouterAnalyst import DORARouterAnalyst
from src.main.util import CostAttributes, getEnglishMeaning, FileActions, Logger

from src.main.transportMode.BicycleTransportMode import BicycleTransportMode


class DORARouterAnalystBicycle_PostGISServiceTest(unittest.TestCase):
    def setUp(self):
        # self.wfsServiceProvider = WFSServiceProvider(wfs_url="http://localhost:9000/geoserver/wfs?",
        #                                              nearestVertexTypeName="tutorial:dgl_nearest_vertex",
        #                                              nearestCarRoutingVertexTypeName="tutorial:dgl_nearest_car_routable_vertex",
        #                                              shortestPathTypeName="tutorial:dgl_shortest_path",
        #                                              outputFormat="application/json")
        self.postgisServiceProvider = PostgisServiceProvider()
        self.transportMode = BicycleTransportMode(self.postgisServiceProvider)
        self.doraRouterAnalyst = DORARouterAnalyst(self.transportMode)
        self.fileActions = FileActions()
        self.dir = os.getcwd()

    def test_givenNoneWFSService_Then_ThrowError(self):
        metroAccessDigiroad = DORARouterAnalyst(None)
        self.assertRaises(TransportModeNotDefinedException, metroAccessDigiroad.calculateTotalTimeTravel, "", "", "", "")

    def test_givenEmtpyURL_Then_ThrowError(self):
        inputCoordinatesURL = None
        outputFolderFeaturesURL = None
        testPolygonsURL = None

        self.assertRaises(NotURLDefinedException,
                          self.doraRouterAnalyst.calculateTotalTimeTravel,
                          inputCoordinatesURL,
                          inputCoordinatesURL,
                          outputFolderFeaturesURL,
                          testPolygonsURL)

    def test_givenAPointGeojson_then_returnGeojsonFeatures(self):
        inputCoordinatesURL = self.dir + '%src%test%data%geojson%empty_FROM_points.geojson'.replace("%", os.sep)
        input2CoordinatesURL = self.dir + '%src%test%data%geojson%empty_TO_points.geojson'.replace("%", os.sep)
        outputFolderFeaturesURL = self.dir + '%src%test%data%outputFolderWhitePoints%'.replace("%", os.sep)
        expectedResultPath = self.dir + '%src%test%data%geojson%shortpathBetweenTwoPoints-Bicycle.geojson'.replace("%",
                                                                                                                os.sep)

        # distanceCostAttribute = CostAttributes.BICYCLE_FAST_TIME
        distanceCostAttribute = {
            # "DISTANCE": CostAttributes.DISTANCE,
            "BICYCLE_FAST_TIME": CostAttributes.BICYCLE_FAST_TIME,
            # "BICYCLE_SLOW_TIME": CostAttributes.BICYCLE_SLOW_TIME,
        }

        prefix = os.path.basename(inputCoordinatesURL) + "_" + os.path.basename(input2CoordinatesURL) + "_log."

        Logger.configureLogger(outputFolderFeaturesURL, prefix)

        self.doraRouterAnalyst.calculateTotalTimeTravel(startCoordinatesGeojsonFilename=inputCoordinatesURL,
                                                        endCoordinatesGeojsonFilename=input2CoordinatesURL,
                                                        outputFolderPath=outputFolderFeaturesURL,
                                                        costAttribute=distanceCostAttribute)

        inputCoordinatesGeojson = self.fileActions.readJson(inputCoordinatesURL)
        expectedResult = self.fileActions.readJson(expectedResultPath)

        if not outputFolderFeaturesURL.endswith(os.sep):
            geomsOutputFolderFeaturesURL = outputFolderFeaturesURL + os.sep + \
                                           "geoms" + os.sep + \
                                           getEnglishMeaning(CostAttributes.BICYCLE_FAST_TIME) + os.sep
        else:
            geomsOutputFolderFeaturesURL = outputFolderFeaturesURL + "geoms" + os.sep + getEnglishMeaning(
                CostAttributes.BICYCLE_FAST_TIME) + os.sep

        outputFileList = self.readOutputFolderFiles(geomsOutputFolderFeaturesURL)

        outputFilename = outputFileList[0]
        outputFilePath = outputFolderFeaturesURL + os.sep + "geoms" + os.sep + getEnglishMeaning(
            CostAttributes.BICYCLE_FAST_TIME) + os.sep + outputFilename

        outputResult = self.fileActions.readJson(outputFilePath)

        for feature in expectedResult["features"]:
            if "id" in feature:
                del feature["id"]

        maxSeq = 0
        for feature in outputResult["features"]:
            maxSeq = max(feature["properties"]["seq"], maxSeq)
            if "id" in feature:
                del feature["id"]

        self.assertEqual(expectedResult, outputResult)

    @unittest.skip("")  # about 13 m for 12 points (132 possible paths)
    def test_givenAMultiPointGeojson_then_returnGeojsonFeatures(self):
        inputStartCoordinatesURL = self.dir + '%src%test%data%geojson%reititinTestPoints.geojson'.replace("%", os.sep)
        inputEndCoordinatesURL = self.dir + '%src%test%data%geojson%reititinTestPoints.geojson'.replace("%", os.sep)

        # inputStartCoordinatesURL = self.dir + '%src%test%data%geojson%not-fast-points.geojson'.replace("%", os.sep)
        # inputEndCoordinatesURL = self.dir + '%src%test%data%geojson%not-fast-points2.geojson'.replace("%", os.sep)
        # outputFolderFeaturesURL = self.dir + '%src%test%data%outputFolderNotFast3%'.replace("%", os.sep)
        outputFolderFeaturesURL = self.dir + '%src%test%data%outputFolder%'.replace("%", os.sep)

        # distanceCostAttribute = CostAttributes.BICYCLE_FAST_TIME
        distanceCostAttribute = {
            # "DISTANCE": CostAttributes.DISTANCE,
            "BICYCLE_FAST_TIME": CostAttributes.BICYCLE_FAST_TIME
            # "BICYCLE_SLOW_TIME": CostAttributes.BICYCLE_SLOW_TIME,
        }

        prefix = CostAttributes.BICYCLE_FAST_TIME + "_log."

        Logger.configureLogger(outputFolderFeaturesURL, prefix)
        self.doraRouterAnalyst.calculateTotalTimeTravel(startCoordinatesGeojsonFilename=inputStartCoordinatesURL,
                                                        endCoordinatesGeojsonFilename=inputEndCoordinatesURL,
                                                        outputFolderPath=outputFolderFeaturesURL,
                                                        costAttribute=distanceCostAttribute)

        inputCoordinatesGeojson = self.fileActions.readJson(inputStartCoordinatesURL)
        for key in distanceCostAttribute:
            if not outputFolderFeaturesURL.endswith(os.sep):
                geomsOutputFolderFeaturesURL = outputFolderFeaturesURL + os.sep + \
                                               "geoms" + os.sep + getEnglishMeaning(distanceCostAttribute[key]) + os.sep
            else:
                geomsOutputFolderFeaturesURL = outputFolderFeaturesURL + "geoms" + os.sep + getEnglishMeaning(
                    distanceCostAttribute[key]) + os.sep

            outputFileList = self.readOutputFolderFiles(geomsOutputFolderFeaturesURL)

            totalCombinatory = len(inputCoordinatesGeojson["features"]) * len(
                inputCoordinatesGeojson["features"]) - len(
                inputCoordinatesGeojson["features"])
            self.assertEqual(totalCombinatory, len(outputFileList))

    def test_givenAListOfGeojson_then_createSummary(self):
        self.maxDiff = None
        expectedJsonURL = self.dir + '%src%test%data%geojson%metroAccessDigiroadSummaryResult-Bicycle.geojson'.replace("%",
                                                                                                                    os.sep)
        outputFolderFeaturesURL = self.dir + '%src%test%data%outputFolder%'.replace("%", os.sep)

        expectedResult = self.fileActions.readJson(expectedJsonURL)
        self.doraRouterAnalyst.createDetailedSummary(outputFolderFeaturesURL,
                                                     CostAttributes.BICYCLE_FAST_TIME,
                                                       "metroAccessDigiroadSummary.geojson")

        summaryOutputFolderFeaturesURL = outputFolderFeaturesURL + os.sep + "summary" + os.sep
        summaryResult = self.fileActions.readJson(
            summaryOutputFolderFeaturesURL + getEnglishMeaning(
                CostAttributes.BICYCLE_FAST_TIME) + "_metroAccessDigiroadSummary.geojson")

        self.assertEqual(expectedResult, summaryResult)

    def test_givenAShortestPathGeojson_then_calculateTheTotalTravelTime(self):
        shortestPathFile = self.dir + '%src%test%data%geojson%shortestPath-fast_time-bicycle.geojson'.replace(
            "%",
            os.sep
        )
        shortestPath = self.fileActions.readJson(shortestPathFile)

        startPointId, endPointId, totalDistance, totalTravelTime = self.doraRouterAnalyst.calculateSmallSummary(
            shortestPath=shortestPath,
            costAttribute=CostAttributes.BICYCLE_FAST_TIME
        )

        self.assertEqual(0, startPointId)
        self.assertEqual(38, endPointId)
        self.assertEqual(19610.75592183732, totalDistance)
        self.assertEqual(58.30832489071997, totalTravelTime)

    def test_givenOneStartPointGeojsonAndOneEndPointGeojson_then_createMultiPointSummary(self):
        startInputCoordinatesURL = self.dir + '%src%test%data%geojson%onePoint.geojson'.replace("%", os.sep)
        endInputCoordinatesURL = self.dir + '%src%test%data%geojson%anotherPoint.geojson'.replace("%", os.sep)
        outputFolderFeaturesURL = self.dir + '%src%test%data%outputFolder%'.replace("%", os.sep)

        expectedJsonURL = self.dir + '%src%test%data%geojson%oneToOneCostSummaryAdditionalInfo.geojson'.replace(
            "%", os.sep)

        expectedResult = self.fileActions.readJson(expectedJsonURL)

        self.doraRouterAnalyst.createGeneralSummary(
            startCoordinatesGeojsonFilename=startInputCoordinatesURL,
            endCoordinatesGeojsonFilename=endInputCoordinatesURL,
            costAttribute=CostAttributes.BICYCLE_FAST_TIME,
            outputFolderPath=outputFolderFeaturesURL,
            outputFilename="oneToOneCostSummary"
        )

        summaryOutputFolderFeaturesURL = outputFolderFeaturesURL + os.sep + "summary" + os.sep
        summaryResult = self.fileActions.readJson(
            summaryOutputFolderFeaturesURL + getEnglishMeaning(
                CostAttributes.BICYCLE_FAST_TIME) + "_oneToOneCostSummary.geojson")

        self.assertEqual(expectedResult, summaryResult)

    def test_givenOneStartPointGeojsonAndManyEndPointsGeojson_then_createMultiPointSummary(self):
        startInputCoordinatesURL = self.dir + '%src%test%data%geojson%onePoint.geojson'.replace("%", os.sep)
        endInputCoordinatesURL = self.dir + '%src%test%data%geojson%reititinTestPoints.geojson'.replace("%",
                                                                                                             os.sep)
        outputFolderFeaturesURL = self.dir + '%src%test%data%outputFolder%'.replace("%", os.sep)

        expectedJsonURL = self.dir + '%src%test%data%geojson%oneToManyCostSummaryAdditionalInfo.geojson'.replace(
            "%", os.sep)

        expectedResult = self.fileActions.readJson(expectedJsonURL)

        self.doraRouterAnalyst.createGeneralSummary(
            startCoordinatesGeojsonFilename=startInputCoordinatesURL,
            endCoordinatesGeojsonFilename=endInputCoordinatesURL,
            costAttribute=CostAttributes.BICYCLE_FAST_TIME,
            outputFolderPath=outputFolderFeaturesURL,
            outputFilename="oneToManyCostSummary"
        )

        summaryOutputFolderFeaturesURL = outputFolderFeaturesURL + os.sep + "summary" + os.sep
        summaryResult = self.fileActions.readJson(
            summaryOutputFolderFeaturesURL + getEnglishMeaning(
                CostAttributes.BICYCLE_FAST_TIME) + "_oneToManyCostSummary.geojson")

        self.assertEqual(expectedResult, summaryResult)

    def test_givenManyStartPointsGeojsonAndOneEndPointGeojson_then_createMultiPointSummary(self):
        startInputCoordinatesURL = self.dir + '%src%test%data%geojson%reititinTestPoints.geojson'.replace("%",
                                                                                                               os.sep)
        endInputCoordinatesURL = self.dir + '%src%test%data%geojson%onePoint.geojson'.replace("%", os.sep)
        outputFolderFeaturesURL = self.dir + '%src%test%data%outputFolder'.replace("%", os.sep)

        expectedJsonURL = self.dir + '%src%test%data%geojson%manyToOneCostSummaryAdditionalInfo.geojson'.replace(
            "%", os.sep)

        expectedResult = self.fileActions.readJson(expectedJsonURL)

        self.doraRouterAnalyst.createGeneralSummary(
            startCoordinatesGeojsonFilename=startInputCoordinatesURL,
            endCoordinatesGeojsonFilename=endInputCoordinatesURL,
            costAttribute=CostAttributes.BICYCLE_FAST_TIME,
            outputFolderPath=outputFolderFeaturesURL,
            outputFilename="manyToOneCostSummary"
        )

        summaryOutputFolderFeaturesURL = outputFolderFeaturesURL + os.sep + "summary" + os.sep
        summaryResult = self.fileActions.readJson(
            summaryOutputFolderFeaturesURL + getEnglishMeaning(
                CostAttributes.BICYCLE_FAST_TIME) + "_manyToOneCostSummary.geojson")

        self.assertEqual(expectedResult, summaryResult)

    def test_givenManyStartPointsGeojsonAndManyEndPointsGeojson_then_createMultiPointSummary(self):
        # startInputCoordinatesURL = self.dir + '%src%test%data%geojson%pointsInTheForest.geojson'.replace("%", os.sep)
        # endInputCoordinatesURL = self.dir + '%src%test%data%geojson%rautatientoriPoint.geojson'.replace("%", os.sep)

        # startInputCoordinatesURL = self.dir + '%src%test%data%geojson%empty_FROM_points.geojson'.replace("%", os.sep)
        # endInputCoordinatesURL = self.dir + '%src%test%data%geojson%empty_TO_points.geojson'.replace("%", os.sep)

        startInputCoordinatesURL = self.dir + '%src%test%data%geojson%reititinTestPoints.geojson'.replace("%",
                                                                                                               os.sep)
        endInputCoordinatesURL = self.dir + '%src%test%data%geojson%reititinTestPoints.geojson'.replace("%",
                                                                                                             os.sep)
        outputFolderFeaturesURL = self.dir + '%src%test%data%outputFolderForest%'.replace("%", os.sep)

        expectedJsonURL = self.dir + '%src%test%data%geojson%manyToManyCostSummaryAdditionalInfo.geojson'.replace(
            "%", os.sep)

        expectedResult = self.fileActions.readJson(expectedJsonURL)

        self.doraRouterAnalyst.createGeneralSummary(
            startCoordinatesGeojsonFilename=startInputCoordinatesURL,
            endCoordinatesGeojsonFilename=endInputCoordinatesURL,
            costAttribute=CostAttributes.BICYCLE_FAST_TIME,
            outputFolderPath=outputFolderFeaturesURL,
            outputFilename="manyToManyCostSummary"
        )

        summaryOutputFolderFeaturesURL = outputFolderFeaturesURL + os.sep + "summary" + os.sep
        summaryResult = self.fileActions.readJson(
            summaryOutputFolderFeaturesURL + getEnglishMeaning(
                CostAttributes.BICYCLE_FAST_TIME) + "_manyToManyCostSummary.geojson")

        self.assertEqual(expectedResult, summaryResult)

    ################################################
    @unittest.SkipTest
    def test_givenYKRGridCellPoints_then_createMultiPointSummary(self):
        startInputCoordinatesURL = self.dir + '%src%test%data%geojson%destPoints.geojson'.replace("%",
                                                                                                       os.sep)
        endInputCoordinatesURL = self.dir + '%src%test%data%geojson%bike_missing_values_coordinates.geojson'.replace("%",
                                                                                                                          os.sep)
        outputFolderFeaturesURL = self.dir + '%src%test%data%outputFolderBikeMissingValues%'.replace("%", os.sep)

        # startInputCoordinatesURL = self.dir + '%src%test%data%geojson%sampleYKRGridPoints-100.geojson'.replace("%",
        #                                                                                                           os.sep)
        # endInputCoordinatesURL = self.dir + '%src%test%data%geojson%sampleYKRGridPoints-100.geojson'.replace("%",
        #                                                                                                             os.sep)
        # outputFolderFeaturesURL = self.dir + '%src%test%data%outputFolderYKR-100%'.replace("%", os.sep)

        # expectedJsonURL = self.dir + '%src%test%data%geojson%oneToOneCostSummaryAdditionalInfo.geojson'.replace("%", os.sep)

        # expectedResult = self.fileActions.readJson(expectedJsonURL)

        outputFileName = "bikeMissingValues"
        self.doraRouterAnalyst.createGeneralSummary(
            startCoordinatesGeojsonFilename=startInputCoordinatesURL,
            endCoordinatesGeojsonFilename=endInputCoordinatesURL,
            costAttribute=CostAttributes.DISTANCE,
            outputFolderPath=outputFolderFeaturesURL,
            outputFilename=outputFileName
        )

        summaryOutputFolderFeaturesURL = outputFolderFeaturesURL + os.sep + "summary" + os.sep
        summaryResult = self.fileActions.readJson(
            summaryOutputFolderFeaturesURL + getEnglishMeaning(
                CostAttributes.DISTANCE) + "_%s.geojson" % outputFileName)

        # self.assertEqual(expectedResult, summaryResult)
        self.assertIsNotNone(summaryResult)

    def readOutputFolderFiles(self, outputFeaturesURL):
        outputFileList = []
        for file in os.listdir(outputFeaturesURL):
            if file.endswith(".geojson"):
                outputFileList.append(file)

        return outputFileList

    def test_parallelism(self):
        with Parallel(n_jobs=2, backend="threading", verbose=5) as parallel:
            accumulator = 0.
            n_iter = 0
            while accumulator < 1000:
                results = parallel(delayed(myDelay)(accumulator + i ** 2) for i in range(5))
                accumulator += sum(results)  # synchronization barrier
                n_iter += 1
        print(accumulator, n_iter)

    @unittest.SkipTest
    def test_parallelism2(self):
        vertexIDs = multiprocessing.Queue()
        features = multiprocessing.Queue()
        # Setup a list of processes that we want to run
        pool = multiprocessing.Pool(processes=4)
        processes = [pool.apply_async(func=mySubprocess, args=(vertexIDs, features, x)) for x in range(4)]

        # # Run processes
        # for p in processes:
        #     p.start()
        #
        # # Exit the completed processes
        # for p in processes:
        #     p.join()

        # Get process results from the output queue
        # results = [output.get() for p in processes]
        self.assertRaises(RuntimeError, [p.get() for p in processes])
        # Queue objects should only be shared between processes through inheritance


def mySubprocess(vertexIDs, features, item):
    vertexIDs.put(item)
    features.put(str(item))
    return vertexIDs, features


def myDelay(number):
    # time.sleep(1)
    return sqrt(number)
