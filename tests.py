import unittest
import sys
import shlex
from cStringIO import StringIO
from timeparser import ENDIAN
from jexifs import ConfigurationError
from jexifs import parser
from jexifs import Index
from jexifs import Image
from jexifs import DatetimeAttr
from jexifs import DateAttr
from jexifs import TimeAttr
from jexifs import Tests
from jexifs import Jexifs



class BaseTestCase(unittest.TestCase):
    def setUp(self):
        self.held = sys.stdout
        sys.stdout = StringIO()

    def tearDown(self):
        Index._firstline = None
        Index.format = None
        Index.fmtlist = None
        Index.sep = None
        Image._lineformat = None
        DatetimeAttr._fmt = None
        DateAttr._fmt = None
        TimeAttr._fmt = None
        sys.stdout = self.held

    def init(self, argstring):
        ENDIAN.set('little')
        args = parser.parse_args(shlex.split(argstring))
        ENDIAN.set('big')
        self.jexifs = Jexifs(args)


class TestIndexFormat(BaseTestCase):

    def test_infile(self):
        self.init(r'-i Index/fshort.tbl')
        self.jexifs.printlines()

    def test_infile_f(self):
        self.init(r'-i Index/fshort.tbl -f "name date time"')
        self.jexifs.printlines()

    def test_notinfile_F(self):
        self.init(r'-i Index/nshort.tbl -F "name date time exposure_time"')
        self.jexifs.printlines()

    def test_notinfile_Ff(self):
        self.init(r'-i Index/nshort.tbl -F "name date time exposure_time" -f "name date time"')
        self.jexifs.printlines()

    def test_notinfile(self):
        self.init(r'-i Index/nshort.tbl')
        self.assertRaisesRegexp(
            ConfigurationError,
            'No input-format specified',
            self.jexifs.printlines
            )

    def test_wrongF(self):
        self.assertRaises(
            SystemExit,
            self.init,
            r'-i Index/nshort.tbl -F "name foo bar"'
            )


class TestIndexSorting(BaseTestCase):

    def test_sort_datetime(self):
        self.init(r'-i Index/fshort.tbl -s datetime')
        self.jexifs.printlines()

    def test_sort_date(self):
        self.init(r'-i Index/fshort.tbl -s date')
        self.jexifs.printlines()

    def test_sort_time(self):
        self.init(r'-i Index/fshort.tbl -s time')
        self.jexifs.printlines()

    def test_sort_exposure_time(self):
        self.init(r'-i Index/fshort.tbl -s exposure_time')
        self.jexifs.printlines()

    def test_sort_model(self):
        self.init(r'-i Index/fshort.tbl -s model')
        self.jexifs.printlines()

    def test_sort_path(self):
        self.init(r'-i Index/fshort.tbl -s path')
        self.jexifs.printlines()

    def test_sort_name(self):
        self.init(r'-i Index/fshort.tbl -s name')
        self.jexifs.printlines()

    def test_sort_model(self):
        self.init(r'-i Index/fshort.tbl -s model')
        self.jexifs.printlines()


class TestFileSelection(BaseTestCase):

    def test_t(self):
        self.init(r'Bilder/:jpg -t 20h')
        self.jexifs.printlines()

    def test_ta(self):
        self.init(r'Bilder/:jpg -t 20h -a')
        self.jexifs.printlines()

    def test_tp(self):
        self.init(r'Bilder/:jpg -t 20h -p 2h')
        self.jexifs.printlines()

    def test_tpa(self):
        self.init(r'Bilder/:jpg -t 20h -p 20min -a')
        self.jexifs.printlines()

    def test_d(self):
        self.init(r'Bilder/:jpg -d 9.7.2013')
        self.jexifs.printlines()

    def test_dt(self):
        self.init(r'Bilder/:jpg -d 9.7.2013 -t 8:30')
        self.jexifs.printlines()

    def test_dtp(self):
        self.init(r'Bilder/:jpg -d 9.7.2013 -t 8:30 -p 20min')
        self.jexifs.printlines()

    def test_dtpa(self):
        self.init(r'Bilder/:jpg -d 9.7.2013 -t 8:30 -p 20min -a')
        self.jexifs.printlines()





if __name__ == '__main__':
    unittest.main()
