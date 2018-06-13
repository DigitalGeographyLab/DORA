import os
import time
import unittest

from src.main.reflection import Reflection
from src.main.util import dgl_timer

from src.main.additionalOperations import AbstractAdditionalLayerOperation


class ReflectionTest(unittest.TestCase):
    def setUp(self):
        self.dir = os.getcwd()
        self.reflection = Reflection()

    def test_givenADirectory_retrieveAllDefinedAbstractOperation(self):
        mainPythonModulePath = "src.main.additionalOperations"
        additionalOperationsList = self.reflection.getClasses(
            self.dir,
            mainPythonModulePath,
            AbstractAdditionalLayerOperation
        )

        self.assertGreater(len(additionalOperationsList), 0)
        for the_object in additionalOperationsList:
            self.assertIsInstance(the_object, AbstractAdditionalLayerOperation)

    @unittest.SkipTest  # Deprecated
    def test_givenTheAdditionalOperationsModuleDirectory_retrieveAllOrderedAbstractOperation(self):
        additionalOperationsList = self.reflection.getAbstractAdditionalLayerOperationObjects()
        self.assertGreater(len(additionalOperationsList), 0)
        counter = 1
        for the_object in additionalOperationsList:
            self.assertEqual(counter, the_object.getExecutionOrder())
            counter = counter + 1
            self.assertIsInstance(the_object, AbstractAdditionalLayerOperation)

    def test_givenAbstractAdditionalLayerOperation_then_returnALinkedListWithAllTheAvailableOperations(self):
        additionalLayerOperationLinkedList = self.reflection.getLinkedAbstractAdditionalLayerOperation()
        counter = 0
        while additionalLayerOperationLinkedList.hasNext():
            additionalLayerOperation = additionalLayerOperationLinkedList.next()
            counter = counter + 1
            self.assertIsInstance(additionalLayerOperation, AbstractAdditionalLayerOperation)

        self.assertEqual(4, counter)

    def test_createTimerDecorator(self):
        self.captureProcessDuration(delay=3)

    @dgl_timer
    def captureProcessDuration(self, delay):
        time.sleep(delay)
