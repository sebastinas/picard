# -*- coding: utf-8 -*-

import unittest
from picard import version_to_string, version_from_string, VersionError

class VersionsTest(unittest.TestCase):

    def test_version_to_string_1(self):
        t = [(0, 0, 1, 'dev', 1), '0.0.1dev1']
        self.failUnlessEqual(version_to_string(t[0]), t[1])
        self.failUnlessEqual(t[0], version_from_string(t[1]))

    def test_version_to_string_2(self):
        t = [(1, 1, 0, 'final', 0), '1.1.0final0']
        self.failUnlessEqual(version_to_string(t[0]), t[1])
        self.failUnlessEqual(t[0], version_from_string(t[1]))

    def test_version_to_string_3(self):
        t = [(1, 1, 0, 'dev', 0), '1.1.0dev0']
        self.failUnlessEqual(version_to_string(t[0]), t[1])
        self.failUnlessEqual(t[0], version_from_string(t[1]))

    def test_version_to_string_4(self):
        t = [(1, 0, 2, '', 0), '1.0.2']
        self.assertRaises(AssertionError, version_to_string, (t[0]))
        self.assertRaises(AttributeError, version_from_string, (t[1]))

    def test_version_to_string_5(self):
        t = [(10, 10, 10, 'dev', 10), '10.10.10dev10']
        self.failUnlessEqual(version_to_string(t[0]), t[1])
        self.failUnlessEqual(t[0], version_from_string(t[1]))

    def test_version_to_string_6(self):
        self.assertRaises(TypeError, version_to_string, ('1', 0, 2, 'final', 0))
        self.assertRaises(AssertionError, version_to_string, (1, 0))
        self.assertRaises(TypeError, version_from_string, 1)
