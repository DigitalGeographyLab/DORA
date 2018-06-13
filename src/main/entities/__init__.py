class Point:
    def __init__(self, latitute, longitude, epsgCode):
        """
        Defines a point with latitute and longitude in a specific coordinate reference system.

        :param latitute: latitude.
        :param longitude: longitude.
        :param epsgCode: Coordinate Reference System code.
        """
        self.__latitude = latitute
        self.__longitude = longitude
        self.__epsgCode = epsgCode

    def getLatitude(self):
        return self.__latitude

    def getLongitude(self):
        return self.__longitude

    def getEPSGCode(self):
        return self.__epsgCode

    def setLatitude(self, latitute):
        self.__latitude = latitute

    def setLongitude(self, longitude):
        self.__longitude = longitude

    def setEPSGCode(self, epsgCode):
        self.__epsgCode = epsgCode

    def equals(self, endPoint):
        if not endPoint:
            return False
        return self.getLongitude() == endPoint.getLongitude() and self.getLatitude() == endPoint.getLatitude() and self.getEPSGCode() == endPoint.getEPSGCode()
