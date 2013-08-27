# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

VERSION = '0.3.0'

import os
import sys
import re
import argparse
import pyexiv2
import datetime
import timeparse
import timeparser
from fractions import Fraction

timeparser.TimeFormats.config(try_hard=True)
timeparser.DateFormats.config(try_hard=True)
timeparser.DatetimeFormats.config(try_hard=True)



USAGE = """usage: 
  jexifs -h
  jexifs [PATH:EXT] [OPTIONS]
"""

HELP = """usage: 
  jexifs -h
  jexifs [PATH:EXT] [OPTIONS]

description:
  Image-selection based on their exifdata.


positional argument:
  PATH:EXT                  Use all files anywhere under PATH that ends on EXT.


optional arguments:
  -h, --help                Print this help message and exit.
  -v, --version             Print the program's version and exit.
  -f, --format [FORMAT]     Specify the format of the output.
  -F, --Format [FORMAT]     Jexifs checks the first line of an index-file for
                            informations that helps to interprete the lines'
                            fields. If there is no headline use --Format to
                            specify its format.
  -i, --index [FILE]        Use FILE as index instead of checking jpegs.
  -H, --headline            Print the output's format as first line.
  -s, --sort TAG            Sort all images after TAG.
                            The default order is alphanumerical in regard of the
                            filenames (using the relative path including PATH).
                            Mind that sorting is memory-expensive, because the
                            data of all jpegs (resp. of the index-file) will be
                            loaded into memory. Only use it if needed.

TAG could be path, name, date, time, datetime, exposure_time or model.
FORMAT is an arbitrary sequence of these words (e.g. -f "path - date - time")


arguments for image-selection:

  data:
  -d, --dates DATE [DATE..] Select all images captured at DATE.
  -t, --times TIME [TIME..] Select all images captured at TIME.
  -D, --datetime DATE TIME  Select all images captured at DATE TIME.
                            Use this option multiple times to specify mor than
                            one datetime.
  -e, --exposure-time SEC [SEC2]
                            Select all images whose exposure-time is SEC or
                            between SEC and SEC2.
  -m, --model [MODEL]       Select all images whose been made with MODEL.


  durations:
  -p, --plus [HOURS] [MINUTES] [SECONDS]
                            Defines a duration that starts with a specified time.
                            To be used with --times or --datetime.
  -a, --first-after         Select the first matched image for after each
                            specified time. Use --plus to specify a timespan the
                            image should be in.
                            Mind that this only gives useful results if the
                            the images are sorted by datetime.
"""


class ConfigurationError(argparse.ArgumentTypeError): pass
class PrintStop(Exception): pass


class classproperty(object):
    def __init__(self, f):
        self.f = classmethod(f)
    def __get__(self, *args):
        return self.f.__get__(*args)()


class Attr(object):
    def __init__(self, rvalue=None):
        self.rvalue = rvalue
        self._value = None

    @property
    def value(self):
        if self._value: return self._value
        self._value = self.parse()
        return self._value

    def parse(self):
        return self.rvalue

    def __str__(self):
        return str(self.rvalue)

    def __nonzero__(self):
        return bool(self.rvalue)


#TODO: output-format for single date/time-values
class DatetimeAttr(Attr):
    _fmt = None
    FORMATS = 'DatetimeFormats'
    PARSE = 'parsedatetime'
    @property
    def fmt(self):
        if self._fmt: return self._fmt
        self.__class__._fmt = getattr(timeparser, self.FORMATS)(self.rvalue)
        return self._fmt

    def parse(self):
        return getattr(timeparser, self.PARSE)(self.rvalue, self.fmt)


class DateAttr(DatetimeAttr):
    _fmt = None
    FORMATS = 'DateFormats'
    PARSE = 'parsedate'


class TimeAttr(DatetimeAttr):
    _fmt = None
    FORMATS = 'TimeFormats'
    PARSE = 'parsetime'


class ExposureTimeAttr(Attr):
    def parse(self):
        return Fraction(self.rvalue)


class Image(dict):
    KEYS = {
        'model' : 'Exif.Image.Model',
        'datetime' : 'Exif.Image.DateTime',
        'exposure_time' : 'Exif.Photo.ExposureTime',
        }
    ATTR = {
        'path' : Attr,
        'name' : Attr,
        'datetime' : DatetimeAttr,
        'date' : DateAttr,
        'time' : TimeAttr,
        'exposure_time' : ExposureTimeAttr,
        'model' : Attr
        }
    _lineformat = None

    @classmethod
    def setformat(cls, lineformat):
        for attr in Image.ATTR.keys():
            lineformat = re.sub(r'(?<![\w])(%s)(?![\w])' % attr, r'{\1}', lineformat)
        cls._lineformat = lineformat

    def __init__(self, data):
        super(Image, self).__init__(dict([(k, self.ATTR[k]()) for k in self.ATTR.keys()]))
        if type(data) == str: self.readexif(data)
        else: self.setdata(data)

    def setdata(self, data):
        self.update(dict([(k, self.ATTR[k](v)) for k, v in data.items()]))
        if not self['datetime'] and self['date'] and self['time']:
            self['datetime'].rvalue = ' '.join((data['date'], data['time']))

    def readexif(self, path):
        self['path'] = Attr(path)
        self['name'] = Attr(os.path.basename(path))
        data = pyexiv2.ImageMetadata(path)
        data.read()
        for k, e in self.KEYS.items():
            try: self[k] = self.ATTR[k](data[e].raw_value)
            except KeyError: pass
        if self['datetime']:
            date, time = self['datetime'].rvalue.split()
            self['date'].rvalue = date
            self['time'].rvalue = time

    @classproperty
    def lineformat(cls):
        if cls._lineformat: return cls._lineformat
        if Index.format: cls.setformat(Index.format)
        else: cls._lineformat = '{path} {date} {time} {exposure_time}'
        return cls._lineformat

    def fprint(self):
        print self.lineformat.format(**self)


class Index(object):
    _firstline = None
    format = None
    fmtlist = None
    sep = None

    @classmethod
    def setformat(cls, rawf):
        match = re.search('\W+', rawf)
        cls.sep = match.group() if match else ' '
        fmt = re.findall('\w+', rawf)
        if not all([f in Image.ATTR for f in fmt]):
            raise ConfigurationError('{0} is not a valid format'.format(rawf))
        else:
            cls.format = rawf
            cls.fmtlist = fmt

    def __init__(self, string):
        if string == '-': self._file = sys.stdin
        else: self._file = open(string, 'r')
        self.check_first_line()

    def check_first_line(self):
        firstline = self.file.readline().rstrip('\n')
        try: self.setformat(firstline)
        except ConfigurationError: self._firstline = firstline

    @property
    def file(self):
        return self._file

    @property
    def lines(self):
        if not self.format: raise ConfigurationError('No input-format specified')
        if self._firstline:
            yield dict(zip(self.fmtlist, self._firstline.split(self.sep)))
        for line in self.file:
            yield dict(zip(self.fmtlist, line.rstrip('\n').split(self.sep)))


class Tests(object):
    def __init__(self, args):
        self.model = args.model
        self.exposure_time = args.exposure_time
        self.times = args.times
        self.dates = args.dates
        self.datetimes = args.datetime
        if self.times: self.times = dict([(t, None) for t in sorted(self.times)])
        if self.dates: self.dates.sort()
        if self.datetimes: self.datetimes.sort()
        self.first_after = args.first_after
        self.period = args.hours
        self._tests = list()

    def __call__(self, img):
        return all((test(img) for test in self.tests))

    @property
    def tests(self):
        if self._tests: return self._tests
        if self.exposure_time: self._tests.append(self.check_exposure_time)
        if self.model: self._tests.append(self.check_model)
        if self.dates: self._tests.append(self.check_dates)
        if self.datetimes:
            if self.first_after and self.period:
                self._tests.append(self.first_datetime_in_period)
            elif self.first_after:
                self._tests.append(self.first_after_datetime)
            elif self.period:
                self._tests.append(self.datetime_in_period)
            else:
                self._tests.append(self.on_datetime)
        if self.times:
            if self.first_after and self.period:
                self._tests.append(self.first_time_in_period)
            elif self.first_after:
                self._tests.append(self.first_after_time)
            elif self.period:
                self._tests.append(self.time_in_period)
            else:
                self._tests.append(self.on_time)
        return self._tests


    def check_model(self, img):
        if not img['model']: return False
        return self.model == img['model'].rvalue

    def check_exposure_time(self, img):
        if not img['exposure_time']: return False
        exti = self.exposure_time
        if len(exti) == 1:
            return img['exposure_time'].value == exti[0]
        else:
            return exti[0] <= img['exposure_time'].value < exti[1]

    def check_dates(self, img):
        if not img['date']: return False
        try: d = self.dates[0]
        except IndexError: raise PrintStop
        if d == img['date'].value: return True
        elif d < img['date'].value: self.dates.remove(d)
        return False

####check datetimes
    def first_datetime_in_period(self, img):
        if not img['datetime']: return False
        try: dt = self.datetimes[0]
        except IndexError: raise PrintStop
        if dt <= img['datetime'].value: self.datetimes.remove(dt)
        if dt <= img['datetime'].value < dt + self.period: return True
        return False

    def first_after_datetime(self, img):
        if not img['datetime']: return False
        try: dt = self.datetimes[0]
        except IndexError: raise PrintStop
        if img['datetime'].value >= dt:
            self.datetimes.remove(dt)
            return True
        return False

    def datetime_in_period(self, img):
        if not img['datetime']: return False
        try: dt = self.datetimes[0]
        except IndexError: raise PrintStop
        edt = dt + self.period
        if dt <= img['datetime'].value < edt: return True
        if img['datetime'].value >= edt: self.datetimes.remove(dt)
        return False

    def on_datetime(self, img):
        if not img['datetime']: return False
        try: dt = self.datetimes[0]
        except IndexError: raise PrintStop
        if img['datetime'].value == dt: return True
        if img['datetime'].value > dt: self.datetimes.remove(dt)
        return False

####check times
    def first_time_in_period(self, img):
        if not img['time']: return False
        for t in self.times:
            b = self.times[t]
            et = t + self.period
            self.times[t] = t <= img['time'].value <= et
            if not b and t <= img['time'].value <= et:return True
        return False

    def first_after_time(self, img):
        if not img['time']: return False
        for t in self.times:
            b = self.times[t]
            self.times[t] = t <= img['time'].value
            if not b and t <= img['time'].value:return True
        return False

    def time_in_period(self, img):
        if not img['time']: return False
        for t in self.times:
            if not self.times[t]:
                if t <= img['time'].value:
                    dt = datetime.datetime.combine(img['date'].value, t)
                    self.times[t] = dt + self.period
            if self.times[t]:
                if img['datetime'].value < self.times[t]: return True
                else: self.times[t] = None
        return False

    def on_time(self, img):
        if not img['time']: return False
        return any([t == img['time'].value for t in self.times])


#TODO: action-option to cp, rm or mv the files
class Jexifs(object):
    def __init__(self, args):
        self.args = args
        self.tests = Tests(args)
        self._paths = list()
        self._images = None

    def run(self):
        if self.args.help: print HELP
        elif self.args.version: print VERSION
        else: self.printlines()

    @property
    def images(self):
        if self._images: return self._images
        #make a list from the generator if imgs need to be sorted
        li_or_gen = lambda g: [i for i in g] if self.args.sort else g

        if self.args.index: self._images = li_or_gen(self._fromindex)
        elif self.args.pathext: self._images = li_or_gen(self._frompaths)

        if self.args.sort: self.sort(self.args.sort)
        return self._images

    @property
    def _fromindex(self):
        for data in self.args.index.lines:
            yield Image(data)

    @property
    def _frompaths(self):
        for path in self.paths:
            yield Image(path)

    @property
    def paths(self):
        if self._paths: return self._paths
        path, ext = self.args.pathext.split(':')
        for i,j,k in os.walk(path):
            for f in k:
                if not f.endswith(ext): continue
                self._paths.append(os.path.join(i, f))
        #if imgs won't be sorted make sure paths are...
        if not self.args.sort: self._paths.sort()
        return self._paths

    def sort(self, attr):
        if attr == 'exposure_time':
            self._images.sort(key=lambda i: i[attr].value)
        else:
            self._images.sort(key=lambda i: i[attr].rvalue)

    def printlines(self):
        if self.args.headline: print Image.fmt.translate(None, '{}')
        for img in self.images:
            try:
                if self.tests(img): img.fprint()
            except PrintStop: break


parser = argparse.ArgumentParser(
    prog='jexifs',
    usage=USAGE,
    conflict_handler='resolve',
    )
parser.add_argument(
    'pathext',
    nargs='?',
    default='.:JPG',
    )
parser.add_argument(
    '-h',
    '--help',
    action='store_true',
    )
parser.add_argument(
    '-v',
    '--version',
    action='store_true',
    )
parser.add_argument(
    '-H',
    '--headline',
    action='store_true',
    )
parser.add_argument(
    '-s',
    '--sort',
    default=None,
    )
parser.add_argument(
    '-f',
    '--format',
    type=Image.setformat,
    )
parser.add_argument(
    '-F',
    '--Format',
    type=Index.setformat,
    )
parser.add_argument(
    '-i',
    '--index',
    type=Index,
    const='-',
    nargs='?',
    default=None
    )
parser.add_argument(
    '-d',
    '--dates',
    action=timeparse.ParseDate,
    nargs='+',
    default=None
    )
parser.add_argument(
    '-t',
    '--times',
    action=timeparse.ParseDaytime,
    nargs='+',
    default=None
    )
parser.add_argument(
    '-D',
    '--datetime',
    action=timeparse.AppendDatetime,
    nargs='+',
    default=None
    )
parser.add_argument(
    '-m',
    '--model',
    default=None
    )
parser.add_argument(
    '-e',
    '--exposure_time',
    type=Fraction,
    nargs='+',
    default=None
    )
parser.add_argument(
    '-p',
    '--plus',
    action=timeparse.ParseTimedelta,
    nargs='+',
    default=datetime.timedelta(),
    dest='hours'    #makes ParseTimedelta taking the first value as hours.
    )
parser.add_argument(
    '-a',
    '--first-after',
    action='store_true',
    )


def main():
    try: args = parser.parse_args()
    #if reading stdin will be interrupted
    except (IOError, KeyboardInterrupt) as err:
        print err
        sys.exit(1)

    jexifs = Jexifs(args)

    #set endian to big for parsing the imgs date
    timeparser.ENDIAN.set('big')

    try: jexifs.run()
    except (IOError, KeyboardInterrupt): pass
    except ConfigurationError as err: print err
    finally:
        if jexifs.args.index: jexifs.args.index.file.close()


if __name__ == "__main__": main()


