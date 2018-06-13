import abc

from src.main.carRoutingExceptions import deprecated
from src.main.logic.Operations import Operations
from src.main.util import getConfigurationProperties, PostfixAttribute, FileActions

from src.main.entities import Point


class AbstractAdditionalLayerOperation(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, executionOrder=-1):
        """
        Abstract class to define new operations over the start and end point features properties.

        :param executionOrder: order in which must be executed the new operation.
        """
        self._executionOrder = executionOrder
        self.operations = Operations(FileActions())

    @abc.abstractmethod
    def runOperation(self, featureJson, prefix=""):
        """
        Method to be implemented to add the new operation behaviour.

        :param featureJson: feature properties of the start or end point.
        :param prefix: "startPoint_" or "endPoint_".
        :return: Dictionary/json containing the result values.
        """
        raise NotImplementedError("Should have implemented this")

    @deprecated
    def getExecutionOrder(self):
        return self._executionOrder


class EuclideanDistanceOperation(AbstractAdditionalLayerOperation):
    def __init__(self):
        super(EuclideanDistanceOperation, self).__init__(1)
        self.selectedPointCoordinatesAttribute, self.nearestVertexCoordinatesAttribute, self.coordinatesCRSAttribute = tuple(
            getConfigurationProperties("GEOJSON_LAYERS_ATTRIBUTES")["points_attributes"].split(","))

    def runOperation(self, featureJson, prefix=""):
        """
        Calculate the euclidean distance between the selected point and its nearest routable vertex.

        :param featureJson: feature properties of the start or end point.
        :param prefix: "startPoint_" or "endPoint_".
        :return: Euclidean distance.
        """
        startPoint = Point(
            latitute=featureJson["properties"][self.selectedPointCoordinatesAttribute][1],
            longitude=featureJson["properties"][self.selectedPointCoordinatesAttribute][0],
            epsgCode=featureJson["properties"][self.coordinatesCRSAttribute]
        )
        nearestStartPoint = Point(
            latitute=featureJson["properties"][self.nearestVertexCoordinatesAttribute][1],
            longitude=featureJson["properties"][self.nearestVertexCoordinatesAttribute][0],
            epsgCode=featureJson["properties"][self.coordinatesCRSAttribute]
        )
        newProperties = {
            prefix + PostfixAttribute.EUCLIDEAN_DISTANCE: self.operations.calculateEuclideanDistance(
                startPoint=startPoint,
                endPoint=nearestStartPoint
            )
        }
        return newProperties


class WalkingTimeOperation(AbstractAdditionalLayerOperation):
    def __init__(self):
        super(WalkingTimeOperation, self).__init__(2)
        self.walkingDistanceAttribute, = tuple(
            getConfigurationProperties("GEOJSON_LAYERS_ATTRIBUTES")["walking_distance_attributes"].split(","))
        self.defaultWalkingDistance = float(getConfigurationProperties("WFS_CONFIG")["walkingDistance"])
        self.walkingSpeed = float(getConfigurationProperties("WFS_CONFIG")["walkingSpeed"])

    def runOperation(self, featureJson, prefix=""):
        """
        Calculate the time spend to walk the euclidean distance betweent the selected point and its nearest vertex and
        the average walking time based on the walking distance layer data.

        :param featureJson: feature properties of the start or end point.
        :param prefix: "startPoint_" or "endPoint_".
        :return: The euclidian walking time and average walking time.
        """
        euclideanDistanceStartPoint = 0
        for property in featureJson["properties"]:
            if property.endswith(PostfixAttribute.EUCLIDEAN_DISTANCE):
                euclideanDistanceStartPoint = featureJson["properties"][property]
                break

        if (self.walkingDistanceAttribute in featureJson["properties"]) \
                and (featureJson["properties"][self.walkingDistanceAttribute] is not None):
            walkingDistance = featureJson["properties"][self.walkingDistanceAttribute]
        else:
            walkingDistance = self.defaultWalkingDistance

        euclideanDistanceTime = self.operations.calculateTime(
            euclideanDistanceStartPoint,
            self.walkingSpeed
        )

        walkingDistanceTime = self.operations.calculateTime(
            walkingDistance,
            self.walkingSpeed
        )

        newProperties = {
            prefix + PostfixAttribute.EUCLIDEAN_DISTANCE + PostfixAttribute.WALKING_TIME: euclideanDistanceTime,
            prefix + PostfixAttribute.AVG_WALKING_DISTANCE + PostfixAttribute.WALKING_TIME: walkingDistanceTime,
            prefix + PostfixAttribute.AVG_WALKING_DISTANCE: walkingDistance
        }
        return newProperties


class ParkingTimeOperation(AbstractAdditionalLayerOperation):
    def __init__(self):
        super(ParkingTimeOperation, self).__init__(3)
        self.parkingTimeAttribute, = tuple(
            getConfigurationProperties("GEOJSON_LAYERS_ATTRIBUTES")["parking_time_attributes"].split(","))
        self.defaultParkingTime = float(getConfigurationProperties("WFS_CONFIG")["parkingTime"])

    def runOperation(self, featureJson, prefix=""):
        """
        Add the parking time to the selected point.

        :param featureJson: feature properties of the start or end point.
        :param prefix: "startPoint_" or "endPoint_".
        :return: Parking time.
        """

        parkingTime = self.defaultParkingTime  # default parking time for any place in the metropolitan area rather than the city center
        if (self.parkingTimeAttribute in featureJson["properties"]) \
                and (featureJson["properties"][self.parkingTimeAttribute] is not None):
            parkingTime = float(featureJson["properties"][self.parkingTimeAttribute])

        newProperties = {
            prefix + PostfixAttribute.PARKING_TIME: parkingTime
        }
        return newProperties


class PropertyTransference(AbstractAdditionalLayerOperation):
    def __init__(self):
        super(PropertyTransference, self).__init__()
        self.attributes = []

    def runOperation(self, featureJson, prefix=""):
        newProperties = {}

        for key in featureJson["properties"]:
            if not key.startswith(prefix):
                newProperties[prefix + key] = featureJson["properties"][key]

        return newProperties
