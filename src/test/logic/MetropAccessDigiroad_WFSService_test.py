import os
import unittest

from src.main.carRoutingExceptions import NotURLDefinedException, \
    TransportModeNotDefinedException
from src.main.connection.PostgisServiceProvider import PostgisServiceProvider
from src.main.logic.MetropAccessDigiroad import MetropAccessDigiroadApplication
from src.main.util import CostAttributes, getEnglishMeaning, FileActions

from src.main.transportMode.PrivateCarTransportMode import PrivateCarTransportMode


class MetropAccessDigiroadTest(unittest.TestCase):
    def setUp(self):
        # self.wfsServiceProvider = WFSServiceProvider(wfs_url="http://localhost:9000/geoserver/wfs?",
        #                                              nearestVertexTypeName="tutorial:dgl_nearest_vertex",
        #                                              nearestCarRoutingVertexTypeName="tutorial:dgl_nearest_car_routable_vertex",
        #                                              shortestPathTypeName="tutorial:dgl_shortest_path",
        #                                              outputFormat="application/json")

        geojsonServiceProvider = PostgisServiceProvider()
        self.transportMode = PrivateCarTransportMode(geojsonServiceProvider)
        self.metroAccessDigiroad = MetropAccessDigiroadApplication(self.transportMode)
        self.fileActions = FileActions()
        self.dir = os.getcwd()

    def test_givenNoneWFSService_Then_ThrowError(self):
        metroAccessDigiroad = MetropAccessDigiroadApplication(None)
        self.assertRaises(TransportModeNotDefinedException, metroAccessDigiroad.calculateTotalTimeTravel, "", "", "", "")

    def test_givenEmtpyURL_Then_ThrowError(self):
        inputCoordinatesURL = None
        outputFolderFeaturesURL = None
        testPolygonsURL = None

        self.assertRaises(NotURLDefinedException,
                          self.metroAccessDigiroad.calculateTotalTimeTravel,
                          inputCoordinatesURL,
                          inputCoordinatesURL,
                          outputFolderFeaturesURL,
                          testPolygonsURL)

    def test_givenAPointGeojson_then_returnGeojsonFeatures(self):
        inputCoordinatesURL = self.dir + '%src%test%data%geojson%onePoint.geojson'.replace("%", os.sep)
        input2CoordinatesURL = self.dir + '%src%test%data%geojson%anotherPoint.geojson'.replace("%", os.sep)
        outputFolderFeaturesURL = self.dir + '%src%test%data%outputFolderTemp%'.replace("%", os.sep)
        expectedResultPath = self.dir + '%src%test%data%geojson%shortpathBetweenTwoPoints.geojson'.replace("%", os.sep)

        # distanceCostAttribute = CostAttributes.DISTANCE
        distanceCostAttribute = {
            "DISTANCE": CostAttributes.DISTANCE
            # "SPEED_LIMIT_TIME": CostAttributes.SPEED_LIMIT_TIME,
            # "DAY_AVG_DELAY_TIME": CostAttributes.DAY_AVG_DELAY_TIME,
            # "MIDDAY_DELAY_TIME": CostAttributes.MIDDAY_DELAY_TIME,
            # "RUSH_HOUR_DELAY": CostAttributes.RUSH_HOUR_DELAY
        }
        self.metroAccessDigiroad.calculateTotalTimeTravel(startCoordinatesGeojsonFilename=inputCoordinatesURL,
                                                          endCoordinatesGeojsonFilename=input2CoordinatesURL,
                                                          outputFolderPath=outputFolderFeaturesURL,
                                                          costAttribute=distanceCostAttribute)

        inputCoordinatesGeojson = self.fileActions.readJson(inputCoordinatesURL)
        expectedResult = self.fileActions.readJson(expectedResultPath)

        if not outputFolderFeaturesURL.endswith(os.sep):
            geomsOutputFolderFeaturesURL = outputFolderFeaturesURL + os.sep + \
                                           "geoms" + os.sep + \
                                           getEnglishMeaning(CostAttributes.DISTANCE) + os.sep
        else:
            geomsOutputFolderFeaturesURL = outputFolderFeaturesURL + "geoms" + os.sep + getEnglishMeaning(
                CostAttributes.DISTANCE) + os.sep

        outputFileList = self.readOutputFolderFiles(geomsOutputFolderFeaturesURL)

        outputFilename = outputFileList[0]
        outputFilePath = outputFolderFeaturesURL  + os.sep + "geoms" + os.sep + getEnglishMeaning(
            CostAttributes.DISTANCE) + os.sep + outputFilename


        outputResult = self.fileActions.readJson(outputFilePath)

        for feature in expectedResult["features"]:
            if "id" in feature:
                del feature["id"]
            if "geometry_name" in feature:
                del feature["geometry_name"]

        maxSeq = 0
        for feature in outputResult["features"]:
            maxSeq = max(feature["properties"]["seq"], maxSeq)
            if "id" in feature:
                del feature["id"]
            if "geometry_name" in feature:
                del feature["geometry_name"]

        self.assertEqual(expectedResult, outputResult)

    @unittest.skip("")  # about 13 m for 12 points (132 possible paths)
    def test_givenAMultiPointGeojson_then_returnGeojsonFeatures(self):
        inputCoordinatesURL = self.dir + '%src%test%data%geojson%reititinTestPoints.geojson'.replace("%", os.sep)
        outputFolderFeaturesURL = self.dir + '%src%test%data%outputFolder%'.replace("%", os.sep)

        # distanceCostAttribute = CostAttributes.DISTANCE
        distanceCostAttribute = {
            "DISTANCE": CostAttributes.DISTANCE,
            "SPEED_LIMIT_TIME": CostAttributes.SPEED_LIMIT_TIME,
            "DAY_AVG_DELAY_TIME": CostAttributes.DAY_AVG_DELAY_TIME,
            "MIDDAY_DELAY_TIME": CostAttributes.MIDDAY_DELAY_TIME,
            "RUSH_HOUR_DELAY": CostAttributes.RUSH_HOUR_DELAY
        }
        self.metroAccessDigiroad.calculateTotalTimeTravel(startCoordinatesGeojsonFilename=inputCoordinatesURL,
                                                          endCoordinatesGeojsonFilename=inputCoordinatesURL,
                                                          outputFolderPath=outputFolderFeaturesURL,
                                                          costAttribute=distanceCostAttribute)

        inputCoordinatesGeojson = self.fileActions.readJson(inputCoordinatesURL)
        for key in distanceCostAttribute:
            if not outputFolderFeaturesURL.endswith(os.sep):
                geomsOutputFolderFeaturesURL = outputFolderFeaturesURL + os.sep + \
                                               "geoms" + os.sep + getEnglishMeaning(distanceCostAttribute[key]) + os.sep
            else:
                geomsOutputFolderFeaturesURL = outputFolderFeaturesURL + "geoms" + os.sep + getEnglishMeaning(
                    distanceCostAttribute[key]) + os.sep

            outputFileList = self.readOutputFolderFiles(geomsOutputFolderFeaturesURL)

            totalCombinatory = len(inputCoordinatesGeojson["features"]) * len(inputCoordinatesGeojson["features"]) - len(
                inputCoordinatesGeojson["features"])
            self.assertEqual(totalCombinatory, len(outputFileList))

    def test_givenAListOfGeojson_then_createSummary(self):
        self.maxDiff = None
        expectedJsonURL = self.dir + '%src%test%data%geojson%metroAccessDigiroadSummaryResult.geojson'.replace("%",
                                                                                                                    os.sep)
        outputFolderFeaturesURL = self.dir + '%src%test%data%outputFolder%'.replace("%", os.sep)

        expectedResult = self.fileActions.readJson(expectedJsonURL)
        self.metroAccessDigiroad.createDetailedSummary(outputFolderFeaturesURL,
                                                       CostAttributes.DISTANCE, "metroAccessDigiroadSummary.geojson")

        summaryOutputFolderFeaturesURL = outputFolderFeaturesURL + os.sep + "summary" + os.sep
        summaryResult = self.fileActions.readJson(
            summaryOutputFolderFeaturesURL + getEnglishMeaning(
                CostAttributes.DISTANCE) + "_metroAccessDigiroadSummary.geojson")

        self.assertEqual(expectedResult, summaryResult)

    def test_givenOneStartPointGeojsonAndOneEndPointGeojson_then_createMultiPointSummary(self):
        startInputCoordinatesURL = self.dir + '%src%test%data%geojson%onePoint.geojson'.replace("%", os.sep)
        endInputCoordinatesURL = self.dir + '%src%test%data%geojson%anotherPoint.geojson'.replace("%", os.sep)
        outputFolderFeaturesURL = self.dir + '%src%test%data%outputFolder%'.replace("%", os.sep)

        expectedJsonURL = self.dir + '%src%test%data%geojson%oneToOneCostSummaryAdditionalInfo.geojson'.replace("%", os.sep)

        expectedResult = self.fileActions.readJson(expectedJsonURL)

        self.metroAccessDigiroad.createGeneralSummary(
            startCoordinatesGeojsonFilename=startInputCoordinatesURL,
            endCoordinatesGeojsonFilename=endInputCoordinatesURL,
            costAttribute=CostAttributes.DISTANCE,
            outputFolderPath=outputFolderFeaturesURL,
            outputFilename="oneToOneCostSummary"
        )

        summaryOutputFolderFeaturesURL = outputFolderFeaturesURL + os.sep + "summary" + os.sep
        summaryResult = self.fileActions.readJson(
            summaryOutputFolderFeaturesURL + getEnglishMeaning(
                CostAttributes.DISTANCE) + "_oneToOneCostSummary.geojson")

        self.assertEqual(expectedResult, summaryResult)

    def test_givenOneStartPointGeojsonAndManyEndPointsGeojson_then_createMultiPointSummary(self):
        startInputCoordinatesURL = self.dir + '%src%test%data%geojson%onePoint.geojson'.replace("%", os.sep)
        endInputCoordinatesURL = self.dir + '%src%test%data%geojson%reititinTestPoints.geojson'.replace("%", os.sep)
        outputFolderFeaturesURL = self.dir + '%src%test%data%outputFolder%'.replace("%", os.sep)

        expectedJsonURL = self.dir + '%src%test%data%geojson%oneToManyCostSummaryAdditionalInfo.geojson'.replace("%", os.sep)

        expectedResult = self.fileActions.readJson(expectedJsonURL)

        self.metroAccessDigiroad.createGeneralSummary(
            startCoordinatesGeojsonFilename=startInputCoordinatesURL,
            endCoordinatesGeojsonFilename=endInputCoordinatesURL,
            costAttribute=CostAttributes.DISTANCE,
            outputFolderPath=outputFolderFeaturesURL,
            outputFilename="oneToManyCostSummary"
        )

        summaryOutputFolderFeaturesURL = outputFolderFeaturesURL + os.sep + "summary" + os.sep
        summaryResult = self.fileActions.readJson(
            summaryOutputFolderFeaturesURL + getEnglishMeaning(
                CostAttributes.DISTANCE) + "_oneToManyCostSummary.geojson")

        self.assertEqual(expectedResult, summaryResult)


    def test_givenManyStartPointsGeojsonAndOneEndPointGeojson_then_createMultiPointSummary(self):
        startInputCoordinatesURL = self.dir + '%src%test%data%geojson%reititinTestPoints.geojson'.replace("%", os.sep)
        endInputCoordinatesURL = self.dir + '%src%test%data%geojson%onePoint.geojson'.replace("%", os.sep)
        outputFolderFeaturesURL = self.dir + '%src%test%data%outputFolder%'.replace("%", os.sep)

        expectedJsonURL = self.dir + '%src%test%data%geojson%manyToOneCostSummaryAdditionalInfo.geojson'.replace("%", os.sep)

        expectedResult = self.fileActions.readJson(expectedJsonURL)

        self.metroAccessDigiroad.createGeneralSummary(
            startCoordinatesGeojsonFilename=startInputCoordinatesURL,
            endCoordinatesGeojsonFilename=endInputCoordinatesURL,
            costAttribute=CostAttributes.DISTANCE,
            outputFolderPath=outputFolderFeaturesURL,
            outputFilename="manyToOneCostSummary"
        )

        summaryOutputFolderFeaturesURL = outputFolderFeaturesURL + os.sep + "summary" + os.sep
        summaryResult = self.fileActions.readJson(
            summaryOutputFolderFeaturesURL + getEnglishMeaning(
                CostAttributes.DISTANCE) + "_manyToOneCostSummary.geojson")

        self.assertEqual(expectedResult, summaryResult)


    def test_givenManyStartPointsGeojsonAndManyEndPointsGeojson_then_createMultiPointSummary(self):
        startInputCoordinatesURL = self.dir + '%src%test%data%geojson%reititinTestPoints.geojson'.replace("%", os.sep)
        endInputCoordinatesURL = self.dir + '%src%test%data%geojson%reititinTestPoints.geojson'.replace("%", os.sep)
        outputFolderFeaturesURL = self.dir + '%src%test%data%outputFolder%'.replace("%", os.sep)

        expectedJsonURL = self.dir + '%src%test%data%geojson%manyToManyCostSummaryAdditionalInfo.geojson'.replace("%", os.sep)

        expectedResult = self.fileActions.readJson(expectedJsonURL)

        self.metroAccessDigiroad.createGeneralSummary(
            startCoordinatesGeojsonFilename=startInputCoordinatesURL,
            endCoordinatesGeojsonFilename=endInputCoordinatesURL,
            costAttribute=CostAttributes.DISTANCE,
            outputFolderPath=outputFolderFeaturesURL,
            outputFilename="manyToManyCostSummary"
        )

        summaryOutputFolderFeaturesURL = outputFolderFeaturesURL + os.sep + "summary" + os.sep
        summaryResult = self.fileActions.readJson(
            summaryOutputFolderFeaturesURL + getEnglishMeaning(
                CostAttributes.DISTANCE) + "_manyToManyCostSummary.geojson")

        self.assertEqual(expectedResult, summaryResult)

################################################
    @unittest.SkipTest
    def test_givenYKRGridCellPoints_then_createMultiPointSummary(self):
        startInputCoordinatesURL = self.dir + '%src%test%data%geojson%sampleYKRGridPoints-5.geojson'.replace("%", os.sep)
        endInputCoordinatesURL = self.dir + '%src%test%data%geojson%sampleYKRGridPoints-13000.geojson'.replace("%", os.sep)
        outputFolderFeaturesURL = self.dir + '%src%test%data%outputFolderYKR-5-13000%'.replace("%", os.sep)

        # expectedJsonURL = self.dir + '%src%test%data%geojson%oneToOneCostSummaryAdditionalInfo.geojson'.replace("%", os.sep)

        # expectedResult = self.fileActions.readJson(expectedJsonURL)

        self.metroAccessDigiroad.createGeneralSummary(
            startCoordinatesGeojsonFilename=startInputCoordinatesURL,
            endCoordinatesGeojsonFilename=endInputCoordinatesURL,
            costAttribute=CostAttributes.RUSH_HOUR_DELAY,
            outputFolderPath=outputFolderFeaturesURL,
            outputFilename="YKRCostSummary-5"
        )

        summaryOutputFolderFeaturesURL = outputFolderFeaturesURL + os.sep + "summary" + os.sep
        summaryResult = self.fileActions.readJson(
            summaryOutputFolderFeaturesURL + getEnglishMeaning(
                CostAttributes.RUSH_HOUR_DELAY) + "_YKRCostSummary-5.geojson")

        # self.assertEqual(expectedResult, summaryResult)
        self.assertIsNotNone(summaryResult)

    def readOutputFolderFiles(self, outputFeaturesURL):
        outputFileList = []
        for file in os.listdir(outputFeaturesURL):
            if file.endswith(".geojson"):
                outputFileList.append(file)

        return outputFileList
