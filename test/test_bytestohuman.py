import unittest
import os.path
from picard.util.bytestohuman import BytesToHuman

# enable testing without gettext
try:
    import __builtin__
except ImportError:
    import builtins as __builtin__ #Python 3.0

try:
    a = _('')
except NameError:
    __builtin__.__dict__['_'] = lambda a: a

try:
    a = ungettext('', '', 0)
except NameError:
    def ungettext(a, b, c):
        if c == 1: return a
        return b
    __builtin__.__dict__['ungettext'] = ungettext



class TestBytesToHuman(unittest.TestCase):
    def setUp(self):
        pass

    def test_00(self):
        filename = os.path.join('test', 'data', 'bth_test_00.dat')
        init_test = False
        testlist = self._create_testlist()
        if not init_test:
            expected = self._read_expected_from(filename)
            self.maxDiff = None
            self.assertListEqual(testlist, expected)
        else:
            self._save_expected_to(filename, testlist)

    def _create_testlist(self):
        values = [0, 1]
        for n in [1000, 1024]:
            p = 1
            for e in range(0,6):
                p *= n
                for x in [0.1, 0.5, 0.99, 0.9999, 1, 1.5]:
                    values.append(int(p*x))
        b = BytesToHuman()
        l = []
        for x in sorted(values) + sorted([-a for a in values]):
            l.append(";".join([str(x), b.decimal(x), b.binary(x), b.decimal_long(x),
                      b.binary_long(x)]))
        return l

    def _save_expected_to(self, path, a_list):
        with open(path, 'wb') as f:
            f.writelines([l + "\n" for l in a_list])
            f.close()

    def _read_expected_from(self, path):
        with open(path, 'rb') as f:
            lines = [l.rstrip("\n") for l in f.readlines()]
            f.close()
            return lines
