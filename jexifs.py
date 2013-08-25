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

VERSION = '0.2.0'

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
  -e, --exposure-time SEC [SEC2]
                            Select all images whose exposure-time is SEC or
                            between SEC and SEC2.
  -m, --model [MODEL]       Select all images whose been made with MODEL.


  durations:
  -p, --plus [HOURS] [MINUTES] [SECONDS]
                            Defines a duration that starts with a specified time.
                            To be used together with --times.
  -a, --first-after         Select the first matched image for after each
                            specified time. Use --plus to specify a timespan the
                            image should be in.
                            Mind that this only gives useful results if the
                            the images are sorted by datetime.
"""


class ConfigurationError(argparse.ArgumentTypeError):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg


class StopLoop(Exception): pass


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
        self.times = args.times
        self.dates = args.dates
        if self.times: self.times.sort()
        if self.dates: self.dates.sort()
        self.model = args.model
        self.exposure_time = args.exposure_time
        self.first_after = args.first_after
        self.period = args.hours
        if self.times: self.timed = dict([(time, None) for time in self.times])

    #TODO: add a datetime-option and test for it, with and without period and
    #first-after
    def __call__(self, img):
        if self.times and not self.check_times(img): return False
        if self.dates and not self.check_dates(img): return False
        if self.exposure_time and not self.check_exposure_time(img): return False
        if self.model and not self.check_model(img): return False
        return True

    def check_model(self, img):
        if not img['model']: return False
        return self.model == img['model'].rvalue

    def check_exposure_time(self, img):
        if not img['exposure_time']: return False
        exti = self.exposure_time
        if len(exti) == 1:
            return img['exposure_time'].value == exti[0]
        else:
            return exti[0] < img['exposure_time'].value < exti[1]

    def check_dates(self, img):
        if not img['date']: return False
        if img['date'].value > self.dates[-1]: raise StopLoop
        return any([date == img['date'].value for date in self.dates])

    def check_times(self, img):
        if not img['time']: return False
        if self.first_after:
            if self.period: return self.first_in_period(img)
            else: return self.first_after_time(img)
        else:
            if self.period: return self.in_period(img)
            else: return self.on_time(img)

    def first_in_period(self, img):
        for time in self.times:
            if self.timed[time]:
                self.timed[time] = img['time'].value > time
            else:
                self.timed[time] = img['time'].value > time
                if self.timed[time] and img['time'].value < time + self.period:
                    return True
        return False

    def first_after_time(self, img):
        for time in self.times:
            if self.timed[time]:
                self.timed[time] = img['time'].value > time
            else:
                self.timed[time] = img['time'].value > time
                if self.timed[time]: return True
        return False

    def in_period(self, img):
        if not img['date']:
            return any([t < img['time'].value < t + self.period for t in self.times])
        else:
            for time in self.times:
                if not self.timed[time]:
                    if img['time'].value > time:
                        self.timed[time] = datetime.datetime.combine(img['date'].value, time)
                if self.timed[time]:
                    if img['datetime'].value < self.timed[time] + self.period:
                        return True
                    else: self.timed[time] = None

    def on_time(self, img):
        return any([t == img['time'].value for t in self.times])


class Jexifs(object):
    def __init__(self, args, tests):
        self.args = args
        self.tests = tests
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
            self._images.sort(key=lambda i: i[attr].value)

    def printlines(self):
        if self.args.headline: print Image.fmt.translate(None, '{}')
        for img in self.images:
            try:
                if self.tests(img): img.fprint()
            except StopLoop: break


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

    jexifs = Jexifs(args, Tests(args))

    #set endian to big for parsing the imgs date
    timeparser.ENDIAN.set('big')

    try: jexifs.run()
    except (IOError, KeyboardInterrupt): pass
    except ConfigurationError as err: print err
    finally:
        if jexifs.args.index: jexifs.args.index.file.close()


if __name__ == "__main__": main()


