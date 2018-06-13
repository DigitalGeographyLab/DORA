import os
import unittest

from src.main.connection.PostgisServiceProvider import PostgisServiceProvider
from src.main.logic.Operations import Operations
from src.main.util import FileActions


class PostgisServiceProviderTest(unittest.TestCase):
    def setUp(self):
        self.postgisServiceProvider = PostgisServiceProvider()
        self.fileActions = FileActions()
        self.operations = Operations(self.fileActions)
        self.dir = os.getcwd()

    def test_createATemporaryTable(self):
        tableName = "temporalTable"
        columns = {
            "uuid": "uuid",
            "ykr_from_id": "INTEGER",
            "ykr_to_id": "INTEGER",
            "travel_time": "DOUBLE PRECISION",
            "travel_time_difference": "DOUBLE PRECISION",
            "geometry": "GEOMETRY",
        }
        try:
            connection = self.postgisServiceProvider.getConnection()
            self.postgisServiceProvider.createTemporaryTable(
                con=connection,
                tableName=tableName,
                columns=columns
            )
        finally:
            connection.close()

    def test_getUUIDCode(self):
        uuid = self.postgisServiceProvider.getUUID(con=self.postgisServiceProvider.getConnection())
        print(uuid)
        self.assertIsNotNone(uuid)

    def test_bucle(self):
        arrayList = [0, 1, 2, 3, 4, 5, 6, 7, 8]
        expected = [[0, 3], [4, 7], [8, 8]]

        jump = 4
        self.assertEqual(expected, self.getModules(arrayList, jump))

        arrayList = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        expected = [[0, 3], [4, 7], [8, 9]]

        self.assertEqual(expected, self.getModules(arrayList, jump))

        arrayList = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        expected = [[0, 3], [4, 7], [8, 10]]

        self.assertEqual(expected, self.getModules(arrayList, jump))

        arrayList = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        expected = [[0, 3], [4, 7], [8, 11]]

        self.assertEqual(expected, self.getModules(arrayList, jump))

        arrayList = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        expected = [[0, 3], [4, 7], [8, 11], [12, 12]]

        self.assertEqual(expected, self.getModules(arrayList, jump))

        arrayList = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        expected = [[0, 2], [3, 5], [6, 8], [9, 11], [12, 12]]
        jump = 3
        self.assertEqual(expected, self.getModules(arrayList, jump))

    def getModules(self, arrayList, jump):
        counter = 0
        intervals = []
        while counter < len(arrayList):
            if counter + jump > len(arrayList):
                jump = len(arrayList) % jump

            intervals.append([counter, counter + jump - 1])
            counter = counter + jump
        print(intervals)
        return intervals
