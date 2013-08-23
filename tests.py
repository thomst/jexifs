import unittest
from timeparser import ENDIAN
from jexifs import parser
from jexifs import Jexifs


class TimeImages(unittest.TestCase):
    def setUp(self):
        args = parser.parse_args('Bilder/:jpg'.split())
        self.j = Jexifs(args)

    def test_images(self):
        foo = self.j.run()


class TimePrintlines(unittest.TestCase):
    def setUp(self):
        args = parser.parse_args('Bilder/:jpg'.split())
        self.j = Jexifs(args)

    def test_printlines(self):
        self.j.run()


class TimeSort(unittest.TestCase):
    def setUp(self):
        args = parser.parse_args('Bilder/:jpg -s datetime'.split())
        self.j = Jexifs(args)

    def test_sort(self):
        self.j.run()


class TimeSelection(unittest.TestCase):
    def setUp(self):
        args = parser.parse_args('Bilder/:jpg -s datetime -t 20h -p 10min'.split())
        self.j = Jexifs(args)

    def test_printlines(self):
        self.j.run()


class TimeIndex(unittest.TestCase):
    def setUp(self):
        args = parser.parse_args("--index table.txt".split())
        self.j = Jexifs(args)

    def test_printlines(self):
        ENDIAN.set('big')
        self.j.run()

class TimeIndexFormat(unittest.TestCase):
    def setUp(self):
        args = parser.parse_args("--index short.tbl -s datetime -t 20h -p 10min -f name-datetime".split())
        self.j = Jexifs(args)

    def test_printlines(self):
        ENDIAN.set('big')
        self.j.run()




if __name__ == '__main__':
    unittest.main()
