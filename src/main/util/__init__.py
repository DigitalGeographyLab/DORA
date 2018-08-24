import configparser
import csv
import datetime
import json
import logging
import logging.config
import numpy
import os
import shutil
import time
import zipfile

from src.main import carRoutingExceptions as exc
from src.main.entities import Point

from pandas.io.json import json_normalize


def enum(**enums):
    return type('Enum', (), enums)


carRountingDictionary = {
    "pituus": "distance",
    "digiroa_aa": "speed_limit_time",
    "kokopva_aa": "day_average_delay_time",
    "keskpva_aa": "midday_delay_time",
    "ruuhka_aa": "rush_hour_delay_time"
}

CostAttributes = enum(DISTANCE='pituus',
                      SPEED_LIMIT_TIME='freeflow',
                      DAY_AVG_DELAY_TIME='kokopva_aa',
                      MIDDAY_DELAY_TIME='keskpva_aa',
                      RUSH_HOUR_DELAY='ruuhka_aa',
                      BICYCLE_FAST_TIME='fast_time',
                      BICYCLE_SLOW_TIME='slow_time')

TransportModes = enum(OSM_PRIVATE_CAR='OSM_PRIVATE_CAR', PRIVATE_CAR='PRIVATE_CAR', BICYCLE='BICYCLE')

GeometryType = enum(POINT="Point", MULTI_POINT='MultiPoint', LINE_STRING='LineString')

PostfixAttribute = enum(EUCLIDEAN_DISTANCE="EuclideanDistance", AVG_WALKING_DISTANCE="AVGWalkingDistance",
                        WALKING_TIME="WalkingTime", PARKING_TIME="ParkingTime")

GPD_CRS = enum(WGS_84={'init': 'EPSG:4326'}, PSEUDO_MERCATOR={'init': 'EPSG:3857'})

def getEnglishMeaning(cost_attribute=None):
    if cost_attribute in carRountingDictionary:
        return carRountingDictionary[cost_attribute]
    else:
        return cost_attribute


def getFormattedDatetime(timemilis=time.time(), format='%Y-%m-%d %H:%M:%S'):
    formattedDatetime = datetime.datetime.fromtimestamp(timemilis).strftime(format)
    return formattedDatetime


def getTimestampFromString(date_string, format='%Y-%m-%d %H:%M:%S'):
    formattedDatetime = datetime.datetime.strptime(date_string, format)
    # return calendar.timegm(formattedDatetime.utctimetuple())
    return formattedDatetime.timestamp()


def timeDifference(startTime, endTime):
    totalTime = (endTime - startTime) / 60  # min
    return totalTime


def getConfigurationProperties(section="WFS_CONFIG"):
    config = configparser.ConfigParser()
    configurationPath = os.getcwd() + "%src%resources%configuration.properties".replace("%", os.sep)
    config.read(configurationPath)
    return config[section]


def extractCRS(geojson):
    epsgCode = geojson["crs"]["properties"]["name"].split(":")[-3] + ":" + \
               geojson["crs"]["properties"]["name"].split(":")[-1]
    return epsgCode


def createPointFromPointFeature(newFeaturePoint, epsgCode):
    if newFeaturePoint["geometry"]["type"] == GeometryType.MULTI_POINT:
        startNearestVertexCoordinates = newFeaturePoint["geometry"]["coordinates"][0]
    elif newFeaturePoint["geometry"]["type"] == GeometryType.POINT:
        startNearestVertexCoordinates = newFeaturePoint["geometry"]["coordinates"]

    nearestStartPoint = Point(latitute=startNearestVertexCoordinates[1],
                              longitude=startNearestVertexCoordinates[0],
                              epsgCode=epsgCode)
    return nearestStartPoint


def dgl_timer(func):
    def func_wrapper(*args, **kwargs):
        timerEnabled = "True".__eq__(getConfigurationProperties(section="WFS_CONFIG")["timerEnabled"])
        if timerEnabled:
            functionName = func.__name__
            startTime = time.time()
            Logger.getInstance().info("%s Start Time: %s" % (functionName, getFormattedDatetime(timemilis=startTime)))

            ###############################
            returns = func(*args, **kwargs)
            ###############################

            endTime = time.time()
            Logger.getInstance().info("%s End Time: %s" % (functionName, getFormattedDatetime(timemilis=endTime)))

            totalTime = timeDifference(startTime, endTime)
            Logger.getInstance().info("%s Total Time: %s m" % (functionName, totalTime))

            return returns
        else:
            return func(*args, **kwargs)

    return func_wrapper


def dgl_timer_enabled(func):
    def func_wrapper(*args, **kwargs):
        functionName = func.__name__
        startTime = time.time()
        Logger.getInstance().info("%s Start Time: %s" % (functionName, getFormattedDatetime(timemilis=startTime)))

        ###############################
        returns = func(*args, **kwargs)
        ###############################

        endTime = time.time()
        Logger.getInstance().info("%s End Time: %s" % (functionName, getFormattedDatetime(timemilis=endTime)))

        totalTime = timeDifference(startTime, endTime)
        Logger.getInstance().info("%s Total Time: %s m" % (functionName, totalTime))

        return returns

    return func_wrapper


class AbstractLinkedList(object):
    def __init__(self):
        self._next = None

    def hasNext(self):
        return self._next is not None

    def next(self):
        self._next

    def setNext(self, next):
        self._next = next


class Node:
    def __init__(self, item):
        """
        A node contains an item and a possible next node.
        :param item: The referenced item.
        """
        self._item = item
        self._next = None

    def getItem(self):
        return self._item

    def setItem(self, item):
        self._item = item

    def getNext(self):
        return self._next

    def setNext(self, next):
        self._next = next


class LinkedList(AbstractLinkedList):
    def __init__(self):
        """
        Linked List implementation.

        The _head is the first node in the linked list.
        _next refers to the possible next node into the linked list.
        And the _tail is the last node added into the linked list.
        """
        self._head = None
        self._next = None
        self._tail = None

    def hasNext(self):
        """
        Veryfy if there is a possible next node in the queue of the linked list.

        :return: True if there is a next node.
        """
        if self._next:
            return True

        return False

    def next(self):
        """
        :return: The next available item in the queue of the linked list.
        """
        item = self._next.getItem()
        self._next = self._next.getNext()
        return item

    def add(self, newItem):
        """
        Add new items into the linked list. The _tail is moving forward and create a new node ecah time that a new item
        is added.

        :param newItem: Item to be added.
        """
        if self._head is None:
            self._head = Node(newItem)
            self._next = self._head
            self._tail = self._head
        else:
            node = Node(newItem)
            self._tail.setNext(node)
            self._tail = node

    def restart(self):
        """
        Move the linked list to its initial node.
        """
        self._next = self._head
        self._tail = self._head


class FileActions:
    def readJson(self, url):
        """
        Read a json file
        :param url: URL for the Json file
        :return: json dictionary data
        """
        with open(url) as f:
            data = json.load(f)
        return data

    def readMultiPointJson(self, url):
        """
        Read a MultiPoint geometry geojson file, in case the file do not be a MultiPoint
        geometry, then an NotMultiPointGeometryException is thrown.

        :param url: URL for the Json file
        :return: json dictionary data
        """
        data = None
        with open(url) as f:
            data = json.load(f)

        self.checkGeometry(data, GeometryType.MULTI_POINT)

        return data

    def readPointJson(self, url):
        """
        Read a MultiPoint geometry geojson file, in case the file do not be a MultiPoint
        geometry, then an NotMultiPointGeometryException is thrown.

        :param url: URL for the Json file
        :return: json dictionary data
        """
        data = None
        with open(url) as f:
            data = json.load(f)

        self.checkGeometry(data, GeometryType.POINT)

        return data

    def checkGeometry(self, data, geometryType=GeometryType.MULTI_POINT):
        """
        Check the content of the Json to verify if it is a specific geoemtry type. By default is MultiPoint.
        In case the geojson do not be the given geometry type then an

        :param data: json dictionary
        :param geometryType: Geometry type (i.e. MultiPoint, LineString)
        :return: None
        """
        for feature in data["features"]:
            if feature["geometry"]["type"] != geometryType:
                raise exc.IncorrectGeometryTypeException("Expected %s" % geometryType)

    def convertToGeojson(self, dataframe):
        jsonResult = dataframe.to_json()
        newJson = json.loads(jsonResult)
        newJson["crs"] = {
            "properties": {
                "name": "urn:ogc:def:crs:%s" % (GPD_CRS.PSEUDO_MERCATOR["init"].replace(":", "::"))
            },
            "type": "name"
        }
        return newJson

    def writeFile(self, folderPath, filename, data):
        if not os.path.exists(folderPath):
            os.makedirs(folderPath)

        fileURL = folderPath + "%s%s" % (os.sep, filename)

        with open(fileURL, 'w+') as outfile:
            json.dump(data, outfile, sort_keys=True)

        return fileURL

    def createFile(self, folderPath, filename):
        if not os.path.exists(folderPath):
            os.makedirs(folderPath)
        with open(folderPath + os.sep + filename, 'w+') as outfile:
            outfile.close()

    def deleteFile(self, folderPath, filename):
        Logger.getInstance().info("Deleting FILE %s" % os.path.join(folderPath, filename))
        if os.path.exists(folderPath + os.sep + filename):
            os.remove(folderPath + os.sep + filename)
        Logger.getInstance().info("The FILE %s was deleted" % os.path.join(folderPath, filename))

    def deleteFolder(self, path):
        Logger.getInstance().info("Deleting FOLDER %s" % path)
        if os.path.exists(path):
            shutil.rmtree(path)
        Logger.getInstance().info("The FOLDER %s was deleted" % path)

    @dgl_timer
    def compressOutputFile(self, folderPath, zip_filename, filepath):
        zipf = zipfile.ZipFile(folderPath + os.sep + zip_filename, "a", zipfile.ZIP_DEFLATED, allowZip64=True)
        zipf.write(filepath, os.path.basename(filepath))

    @dgl_timer
    def transformGeojsonInDataFrame(self, geojson):
        if "features" in geojson:
            df = json_normalize(geojson["features"])
            columns = numpy.asarray([column.replace("properties.", "") for column in df.columns.values])
            df.columns = columns
            return df

        return None

    def writeInCSV(self, folderPath, filename, valueList):
        if not os.path.exists(folderPath):
            os.makedirs(folderPath)

        file = folderPath + os.sep + filename

        if not os.path.isfile(file):
            fieldList = []

            attributes = getConfigurationProperties(section="ATTRIBUTES_MAPPING")

            for attribute_key in attributes:
                attribute_splitted = attributes[attribute_key].split(",")
                key = attribute_splitted[0]
                value = attribute_splitted[1]
                fieldList.append(value)

            with open(file, 'w', newline='') as outputFile:
                writer = csv.writer(outputFile, delimiter=';')
                writer.writerow(fieldList)
                writer.writerow(valueList)
        else:
            with open(file, 'a', newline='') as outputFile:
                writer = csv.writer(outputFile, delimiter=';')
                writer.writerow(valueList)


def parallel_job_print(msg, msg_args):
    """ Display the message on stout or stderr depending on verbosity
    """
    # XXX: Not using the logger framework: need to
    # learn to use logger better.
    # if not self.verbose:
    #     return
    # if self.verbose < 50:
    #     writer = sys.stderr.write
    # else:
    #     writer = sys.stdout.write
    msg = msg % msg_args
    self = "Parallel(n_jobs=%s)" % getConfigurationProperties(section="PARALLELIZATION")["jobs"]
    # writer('[%s]: %s\n' % (self, msg))
    Logger.getInstance().info('[%s]: %s' % (self, msg))


class Logger:
    __instance = None
    __handler = None

    def __init__(self):
        raise Exception("Instances must be constructed with Logger.getInstance()")

    @staticmethod
    def configureLogger(outputFolder, prefix):
        # Logger.__instance = None

        log_filename = prefix + "_log - %s.log" % getFormattedDatetime(timemilis=time.time(),
                                                                       format='%Y-%m-%d %H_%M_%S')
        logs_folder = outputFolder + os.sep + "logs"

        FileActions().createFile(logs_folder, log_filename)

        if Logger.__handler is not None:
            Logger.getInstance().removeHandler(Logger.__handler)

        fileHandler = logging.FileHandler(logs_folder + os.sep + log_filename, 'w')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fileHandler.setFormatter(formatter)

        Logger.__handler = fileHandler

        Logger.getInstance().addHandler(fileHandler)

    @staticmethod
    def getInstance():
        if not Logger.__instance:
            # configurationPath = os.getcwd() + "%resources%logging.properties".replace("%", os.sep)

            # logging.config.fileConfig(configurationPath)

            # create logger
            Logger.__instance = logging.getLogger("CARDAT")
        # "application" code
        # Logger.instance.debug("debug message")
        # Logger.instance.info("info message")
        # Logger.instance.warn("warn message")
        # Logger.instance.error("error message")
        # Logger.instance.critical("critical message")
        return Logger.__instance


class GeneralLogger:
    def __init__(self, loggerName, outputFolder, prefix=""):
        self.logger = self._createLogger(loggerName=loggerName)
        self.handler = self._createLogFileHandler(outputFolder=outputFolder, prefix=prefix)

        self.logger.addHandler(self.handler)

    def _createLogger(self, loggerName):
        configurationPath = os.getcwd() + "%src%resources%logging.properties".replace("%", os.sep)
        logging.config.fileConfig(configurationPath)
        # create logger
        logger = logging.getLogger(loggerName)
        return logger

    def _createLogFileHandler(self, outputFolder, prefix):
        log_filename = prefix + "_log - %s.log" % getFormattedDatetime(
            timemilis=time.time(),
            format='%Y-%m-%d %H_%M_%S'
        )
        logs_folder = outputFolder + os.sep + "logs"
        FileActions().createFile(logs_folder, log_filename)

        fileHandler = logging.FileHandler(logs_folder + os.sep + log_filename, 'w')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fileHandler.setFormatter(formatter)
        return fileHandler

    def getLogger(self):
        return self.logger
