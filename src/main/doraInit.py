import gc
import getopt
import os
import sys
import time
import traceback

import psutil

from src.main.carRoutingExceptions import ImpedanceAttributeNotDefinedException, NotParameterGivenException, \
    TransportModeNotDefinedException
from src.main.connection.PostgisServiceProvider import PostgisServiceProvider
from src.main.logic.MetropAccessDigiroad import MetropAccessDigiroadApplication
from src.main.util import CostAttributes, getConfigurationProperties, TransportModes, Logger, getFormattedDatetime, \
    GeneralLogger, timeDifference

from src.main.transportMode.BicycleTransportMode import BicycleTransportMode
from src.main.transportMode.PrivateCarTransportMode import PrivateCarTransportMode


def printHelp():
    # print(
    #     "DigiroadPreDataAnalysis tool\n"
    #     "\n\t[--help]: Print information about the parameters necessary to run the tool."
    #     "\n\t[-s, --start_point]: Geojson file containing all the pair of points to calculate the shortest path between them."
    #     "\n\t[-e, --end_point]: Geojson file containing all the pair of points to calculate the shortest path between them."
    #     "\n\t[-o, --outputFolder]: The final destination where the output geojson and summary files will be located."
    #     "\n\t[-c, --costAttributes]: The impedance/cost attribute to calculate the shortest path."
    #     "\n\t[-t, --transportMode]: The transport mode used to calculate the shortest path."
    #     "\n\t[--routes]: Only calculate the shortest path."
    #     "\n\t[--summary]: Only the cost summary should be calculated."
    #     "\n\t[--is_entry_list]: The start and end points entries are folders containing a list of geojson files."
    #     "\n\t[--all]: Calculate the shortest path to all the impedance/cost attributes."
    #     "\n\nImpedance/cost values allowed:"
    #     "\n\tDISTANCE"
    #     "\n\tSPEED_LIMIT_TIME"
    #     "\n\tDAY_AVG_DELAY_TIME"
    #     "\n\tMIDDAY_DELAY_TIME"
    #     "\n\tRUSH_HOUR_DELAY"
    # )
    pass


def main():
    """
    Read the arguments written in the command line to read the input coordinates from a
    Geojson file (a set of pair points) and the location (URL) to store the Shortest Path geojson features for each
    pair of points.

    Call the ``calculateTotalTimeTravel`` from the WFSServiceProvider configured
    with the parameters in './resources/configuration.properties' and calculate the shortest path for each
    pair of points and store a Geojson file per each of them.

    After that, call the function ``createSummary`` to summarize the total time expend to go from one point to another
    for each of the different impedance attribute (cost).

    :return: None. All the information is stored in the ``shortestPathOutput`` URL.
    """

    argv = sys.argv[1:]
    opts, args = getopt.getopt(
        argv, "s:e:o:c:t:",
        ["start_point=", "end_point=", "outputFolder=", "costAttributes=",
         "transportMode", "is_entry_list", "routes", "summary", "all", "help"]
    )

    startPointsGeojsonFilename = None
    outputFolder = None
    # impedance = CostAttributes.DISTANCE
    # impedance = None
    impedanceList = []

    car_impedances = {
        "DISTANCE": CostAttributes.DISTANCE,
        "SPEED_LIMIT_TIME": CostAttributes.SPEED_LIMIT_TIME,
        "DAY_AVG_DELAY_TIME": CostAttributes.DAY_AVG_DELAY_TIME,
        "MIDDAY_DELAY_TIME": CostAttributes.MIDDAY_DELAY_TIME,
        "RUSH_HOUR_DELAY": CostAttributes.RUSH_HOUR_DELAY

    }

    bicycle_impedances = {
        "DISTANCE": CostAttributes.DISTANCE,
        "BICYCLE_FAST_TIME": CostAttributes.BICYCLE_FAST_TIME,
        "BICYCLE_SLOW_TIME": CostAttributes.BICYCLE_SLOW_TIME

    }

    allImpedanceAttribute = False
    summaryOnly = False
    routesOnly = False
    isEntryList = False

    impedanceErrorMessage = "Use the paramenter -c or --cost.\nValues allowed: DISTANCE, SPEED_LIMIT_TIME, DAY_AVG_DELAY_TIME, MIDDAY_DELAY_TIME, RUSH_HOUR_DELAY.\nThe parameter --all enable the analysis for all the impedance attributes."
    transportModeErrorMessage = "Use the paramenter -t or --transportMode.\nValues allowed: PRIVATE_CAR, BICYCLE."

    for opt, arg in opts:
        if opt in "--help":
            printHelp()
            return

        # print("options: %s, arg: %s" % (opt, arg))

        if opt in ("-s", "--start_point"):
            startPointsGeojsonFilename = arg

        if opt in ("-e", "--end_point"):
            endPointsGeojsonFilename = arg

        if opt in ("-o", "--outputFolder"):
            outputFolder = arg

        if opt in ("-t", "--transportMode"):
            transportModeSelected = arg

        if opt in "--summary":
            summaryOnly = True
        if opt in "--routes":
            routesOnly = True

        if opt in "--is_entry_list":
            isEntryList = True

        if opt in "--all":
            allImpedanceAttribute = True
        else:
            if opt in ("-c", "--costAttributes"):
                impedanceListTemp = arg.split(",")
                for impedanceArg in impedanceListTemp:
                    if (impedanceArg not in car_impedances) and (impedanceArg not in bicycle_impedances):
                        raise ImpedanceAttributeNotDefinedException(
                            impedanceErrorMessage)

                    if impedanceArg in car_impedances:
                        impedance = car_impedances[impedanceArg]
                    elif impedanceArg in bicycle_impedances:
                        impedance = bicycle_impedances[impedanceArg]

                    impedanceList.append(impedance)

    if not startPointsGeojsonFilename or not endPointsGeojsonFilename or not outputFolder:
        raise NotParameterGivenException("Type --help for more information.")

    if not transportModeSelected:
        raise TransportModeNotDefinedException(
            transportModeErrorMessage)

    if not allImpedanceAttribute and not impedance:
        raise ImpedanceAttributeNotDefinedException(
            impedanceErrorMessage)

    generalLogger = GeneralLogger(loggerName="GENERAL", outputFolder=outputFolder, prefix="General")
    MAX_TRIES = 2
    RECOVERY_WAIT_TIME = 10
    RECOVERY_WAIT_TIME_8_MIN = 480

    postgisServiceProvider = PostgisServiceProvider()

    transportMode = None
    impedances = None

    if transportModeSelected == TransportModes.BICYCLE:
        transportMode = BicycleTransportMode(postgisServiceProvider)
        impedances = bicycle_impedances
    elif transportModeSelected == TransportModes.PRIVATE_CAR:
        transportMode = PrivateCarTransportMode(postgisServiceProvider)
        impedances = car_impedances

    starter = MetropAccessDigiroadApplication(
        transportMode=transportMode
    )

    startTime = time.time()
    functionName = "Routing Data Analysis"
    generalLogger.getLogger().info("%s Start Time: %s" % (functionName, getFormattedDatetime(timemilis=startTime)))
    if not isEntryList:
        prefix = os.path.basename(startPointsGeojsonFilename) + "_" + os.path.basename(endPointsGeojsonFilename)
        error_counts = 0
        executed = False

        while not executed:
            try:
                generalLogger.getLogger().info("Analyzing %s" % prefix)
                executeSpatialDataAnalysis(outputFolder, startPointsGeojsonFilename, endPointsGeojsonFilename,
                                           starter,
                                           impedanceList, impedances, allImpedanceAttribute,
                                           summaryOnly,
                                           routesOnly,
                                           prefix)
                error_counts = 0
                executed = True
                gc.collect()
            except Exception as err:
                error_counts += 1
                exc_type, exc_value, exc_traceback = sys.exc_info()
                lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
                generalLogger.getLogger().exception(''.join('>> ' + line for line in lines))
                memory = psutil.virtual_memory()
                generalLogger.getLogger().warning(
                    "MEMORY USAGE: total=%s, available=%s, percent=%s, used=%s, free=%s" % (
                        memory.total, memory.available, memory.percent, memory.used,
                        memory.free)
                )

                Logger.getInstance().exception(''.join('>> ' + line for line in lines))

                time.sleep(RECOVERY_WAIT_TIME)
                generalLogger.getLogger().warning("Calling garbage collector...")
                gc.collect()
                time.sleep(RECOVERY_WAIT_TIME_8_MIN)
                memory = psutil.virtual_memory()
                generalLogger.getLogger().warning(
                    "MEMORY USAGE: total=%s, available=%s, percent=%s, used=%s, free=%s" % (
                        memory.total, memory.available, memory.percent, memory.used,
                        memory.free)
                )

                if error_counts < (MAX_TRIES + 1):
                    message = "Error recovery for the %s time%s" % (
                        error_counts, ("" if error_counts < 2 else "s"))
                    generalLogger.getLogger().warning(message)
                    Logger.getInstance().warning(message)
                else:
                    message = "Recurrent error, skipping analysis for: %s" % prefix
                    generalLogger.getLogger().warning(message)
                    Logger.getInstance().warning(message)
                    executed = True
    else:
        for startRoot, startDirs, startFiles in os.walk(startPointsGeojsonFilename):
            for startPointsFilename in startFiles:
                if startPointsFilename.endswith("geojson"):
                    for endRoot, endDirs, endFiles in os.walk(endPointsGeojsonFilename):
                        for endPointsFilename in endFiles:
                            if endPointsFilename.endswith("geojson"):
                                prefix = startPointsFilename + "_" + endPointsFilename
                                error_counts = 0
                                executed = False

                                while not executed:
                                    try:
                                        generalLogger.getLogger().info("Analyzing %s" % prefix)
                                        executeSpatialDataAnalysis(outputFolder,
                                                                   os.path.join(startRoot, startPointsFilename),
                                                                   os.path.join(endRoot, endPointsFilename),
                                                                   starter,
                                                                   impedanceList, impedances, allImpedanceAttribute,
                                                                   summaryOnly,
                                                                   routesOnly,
                                                                   prefix + "-")

                                        error_counts = 0
                                        executed = True
                                        gc.collect()
                                    except Exception as err:
                                        error_counts += 1
                                        exc_type, exc_value, exc_traceback = sys.exc_info()
                                        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
                                        generalLogger.getLogger().exception(''.join('>> ' + line for line in lines))
                                        memory = psutil.virtual_memory()
                                        generalLogger.getLogger().warning(
                                            "MEMORY USAGE: total=%s, available=%s, percent=%s, used=%s, free=%s" % (
                                                memory.total, memory.available, memory.percent, memory.used,
                                                memory.free)
                                        )

                                        Logger.getInstance().exception(''.join('>> ' + line for line in lines))

                                        time.sleep(RECOVERY_WAIT_TIME)
                                        generalLogger.getLogger().warning("Calling garbage collector...")
                                        gc.collect()
                                        time.sleep(RECOVERY_WAIT_TIME_8_MIN)
                                        memory = psutil.virtual_memory()
                                        generalLogger.getLogger().warning(
                                            "MEMORY USAGE: total=%s, available=%s, percent=%s, used=%s, free=%s" % (
                                                memory.total, memory.available, memory.percent, memory.used,
                                                memory.free)
                                        )

                                        if error_counts < (MAX_TRIES + 1):
                                            message = "Error recovery for the %s time%s" % (
                                                error_counts, ("" if error_counts < 2 else "s"))
                                            generalLogger.getLogger().warning(message)
                                            Logger.getInstance().warning(message)
                                        else:
                                            message = "Recurrent error, skipping analysis for: %s" % prefix
                                            generalLogger.getLogger().warning(message)
                                            Logger.getInstance().warning(message)
                                            executed = True
    endTime = time.time()
    generalLogger.getLogger().info("%s End Time: %s" % (functionName, getFormattedDatetime(timemilis=endTime)))

    totalTime = timeDifference(startTime, endTime)
    generalLogger.getLogger().info("%s Total Time: %s m" % (functionName, totalTime))


def executeSpatialDataAnalysis(outputFolder, startPointsGeojsonFilename, endPointsGeojsonFilename,
                               starterApplication,
                               impedanceList, impedances, allImpedanceAttribute,
                               summaryOnly,
                               routesOnly,
                               prefix):
    Logger.configureLogger(outputFolder, prefix)
    config = getConfigurationProperties()
    # wfsServiceProvider = WFSServiceProvider(
    #     wfs_url=config["wfs_url"],
    #     nearestVertexTypeName=config["nearestVertexTypeName"],
    #     nearestCarRoutingVertexTypeName=config["nearestCarRoutingVertexTypeName"],
    #     shortestPathTypeName=config["shortestPathTypeName"],
    #     outputFormat=config["outputFormat"]
    # )

    if not allImpedanceAttribute:
        for impedance in impedanceList:
            if routesOnly:
                starterApplication.calculateTotalTimeTravel(
                    startCoordinatesGeojsonFilename=startPointsGeojsonFilename,
                    endCoordinatesGeojsonFilename=endPointsGeojsonFilename,
                    outputFolderPath=outputFolder,
                    costAttribute=impedance
                )

                if summaryOnly:
                    starterApplication.createDetailedSummary(
                        folderPath=outputFolder,
                        costAttribute=impedance,
                        outputFilename=prefix + "metroAccessDigiroadSummary.geojson"
                    )

            elif summaryOnly:
                starterApplication.createGeneralSummary(
                    startCoordinatesGeojsonFilename=startPointsGeojsonFilename,
                    endCoordinatesGeojsonFilename=endPointsGeojsonFilename,
                    costAttribute=impedance,
                    outputFolderPath=outputFolder,
                    outputFilename=prefix + "dijsktraCostMetroAccessDigiroadSummary"
                )

    if allImpedanceAttribute:
        if routesOnly:
            starterApplication.calculateTotalTimeTravel(
                startCoordinatesGeojsonFilename=startPointsGeojsonFilename,
                endCoordinatesGeojsonFilename=endPointsGeojsonFilename,
                outputFolderPath=outputFolder,
                costAttribute=impedances
            )

        for key in impedances:
            if routesOnly and summaryOnly:
                starterApplication.createDetailedSummary(
                    folderPath=outputFolder,
                    costAttribute=impedances[key],
                    outputFilename=prefix + "metroAccessDigiroadSummary.geojson"
                )
            elif summaryOnly:
                starterApplication.createGeneralSummary(
                    startCoordinatesGeojsonFilename=startPointsGeojsonFilename,
                    endCoordinatesGeojsonFilename=endPointsGeojsonFilename,
                    costAttribute=impedances[key],
                    outputFolderPath=outputFolder,
                    outputFilename=prefix + "dijsktraCostMetroAccessDigiroadSummary"
                )
