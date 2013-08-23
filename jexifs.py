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

__version__ = '0.1.0'

import os
import sys
import re
import argparse
import pyexiv2
import timeparse
import timeparser
from fractions import Fraction
from datetime import datetime
from datetime import time
from datetime import timedelta
from datetime import date

timeparser.TimeFormats.config(try_hard=True)
timeparser.DateFormats.config(try_hard=True)
timeparser.DatetimeFormats.config(try_hard=True)


VERSION = '0.1.0'


USAGE = """usage: 
  exifimgs -h
  exifimgs [PATH:EXT] [OPTIONS]
"""

HELP = """usage: 
  exifimgs -h
  exifimgs [PATH:EXT] [OPTIONS]

description:
  Image-selection based on their exifdata.


positional argument:
  PATH:EXT                  Use all files anywhere under PATH that ends on EXT.


optional arguments:
  -h, --help                Print this help message and exit.
  -v, --version              Print the program's version and exit.
  -f, --format [FORMAT]     Specify the format of an index-file.
  -i, --index [FILE]        Use FILE as index instead of checking jpegs.
  -H, --headline            Print the output's format as first line.
  -s, --sort TAG            Sort all images after TAG.
                            The default order is alphanumerical in regard of the
                            filenames (using the relative path including PATH).
                            Mind that sorting is memory-expensive, because the
                            data of all jpegs (resp. of the index-file) will be
                            loaded into memory. Only use it if needed.


arguments for image-selection:

  data:
  -d, --date DATE           Select all images captured at DATE.
  -t, --time TIME           Select all images captured at TIME.
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


known bugs:
  Using a duration that passes midnight won't produce a senseful result:
  --times 22h --plus 4h would look for images that are older than 22h and
  younger than 2h. Date will not be regarded.
"""

class ConfigurationError(argparse.ArgumentTypeError):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg


class Image(object):
    KEYS = {
        'model' : 'Exif.Image.Model',
        'datetime' : 'Exif.Image.DateTime',
        'exposure_time' : 'Exif.Photo.ExposureTime',
        }
    ATTR = (
        'path',
        'name',
        'datetime',
        'date',
        'time',
        'exposure_time',
        'model'
        )
    fmt = '{path} {date} {time} {exposure_time}'

    @classmethod
    def setformat(cls, fmt):
        for attr in Image.ATTR:
            fmt = re.sub(r'(?<![\w])(%s)(?![\w])' % attr, r'{\1}', fmt)
        cls.fmt = fmt

    def __init__(self, data):
        self._data = dict([(k, None) for k in self.ATTR])
        if type(data) == str: self.readexif(data)
        else: self.setdata(data)

    def setdata(self, data):
        self._data.update(data)
        if not self._data['datetime'] and self._data['date'] and self._data['time']:
            self._data['datetime'] = ' '.join((data['date'], data['time']))

    def readexif(self, path):
        self._data['path'] = path
        self._data['name'] = os.path.basename(path)
        data = pyexiv2.ImageMetadata(path)
        data.read()
        for k, e in self.KEYS.items():
            try: self._data[k] = data[e].raw_value
            except KeyError: self._data[k] = None
        if self._data['datetime']:
            date, time = self._data['datetime'].split()
            self._data['date'] = date
            self._data['time'] = time

    @property
    def path(self):
        return self._data['path']

    @property
    def name(self):
        return self._data['name']

    @property
    def datetime(self):
        return self._data['datetime']

    @property
    def date(self):
        return self._data['date']

    @property
    def time(self):
        return self._data['time']

    @property
    def exposure_time(self):
        return self._data['exposure_time']

    @property
    def model(self):
        return self._data['model']

    def fprint(self):
        print self.fmt.format(**self._data)


class Index(object):
    _format = None
    _sep = None
    _firstline = None

    @classmethod
    def setformat(cls, rawf):
        match = re.search('\W+', rawf)
        cls._sep = match.group() if match else ' '
        fmt = re.findall('\w+', rawf)
        if not all([f in Image.ATTR for f in fmt]):
            raise ConfigurationError('{0} is not a valid format'.format(rawf))
        else: cls._format = fmt

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
    def format(self):
        return self._format

    @property
    def sep(self):
        return self._sep

    @property
    def lines(self):
        if not self.format: raise ConfigurationError('No input-format specified')
        if self._firstline:
            yield dict(zip(self.format, self._firstline.split(self.sep)))
        for line in self.file:
            yield dict(zip(self.format, line.rstrip('\n').split(self.sep)))


class Jexifs(object):
    def __init__(self, args):
        self.args = args
        self._paths = list()
        self._images = None
        self._timed = dict()

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
            for img in self._images: img._data['exposure_time'] = Fraction(img.exposure_time)
        self._images.sort(key=lambda i: getattr(i, attr))

    def check_model(self, img):
        return self.args.model == img.model

    def check_exposure_time(self, img):
        exti = self.args.exposure_time
        imgs_exti = Fraction(img.exposure_time)
        if len(exposure_time) == 1:
            return img.exposure_time == exposure_time[0]
        else:
            return exposure_time[0] < img.exposure_time < exposure_time[1]

    #TODO: If I could be sure for chronologity I could stop the program after
    #processing a searched date or datetime.
    def check_dates(self, img):
        if not img.date: return False
        imgs_date = timeparser.parsedate(img.date)
        return any([date == imgs_date for date in self.args.dates])

    @property
    def timed(self):
        if self._timed: return self._timed
        for time in self.args.times: self._timed[time] = False
        return self._timed

    #TODO: -t 22h -p 4h will check for files between 22h and 2h...
    #Maybe I need an extra datetime mode for durations passing days.
    def check_times(self, img):
        if not img.time: return False
        imgs_time = timeparser.parsetime(img.time)
        times = self.args.times
        if self.args.hours:
            if self.args.first_after:
                for time in times:
                    if self.timed[time]:
                        self.timed[time] = imgs_time > time
                    else:
                        self.timed[time] = imgs_time > time
                        if self.timed[time] and imgs_time < time + self.args.hours:
                            return True
                return False
            else:
                return any([t < imgs_time < t + self.args.hours for t in times])
        else:
            return any([t == imgs_time for t in times])

    def printlines(self):
        if self.args.headline: print Image.fmt.translate(None, '{}')
        for img in self.images:
            if self.args.times and not self.check_times(img): continue
            if self.args.dates and not self.check_dates(img): continue
            if self.args.exposure_time and not self.check_exposure_time(img): continue
            if self.args.model and not self.check_model(img): continue
            img.fprint()



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
#TODO: if using an index-file --format should defaults to the index-file's format.
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
    default=timedelta(),
    dest='hours'    #make ParseTimedelta take the first value as hours.
    )
parser.add_argument(
    '-a',
    '--first-after',
    action='store_true',
    )


def main():
    try: jexifs = Jexifs(parser.parse_args())
    except (IOError, KeyboardInterrupt): sys.exit(1)
    timeparser.ENDIAN.set('big')
    try: jexifs.run()
    except (IOError, KeyboardInterrupt): pass
    except ConfigurationError as err: print err
    finally:
        if jexifs.args.index: jexifs.args.index.file.close()


if __name__ == "__main__": main()


