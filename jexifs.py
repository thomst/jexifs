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




USAGE = """usage: 
  exifimgs -h
  exifimgs [PATH] [OPTIONS]
"""

HELP = """usage: 
  exifimgs -h
  exifimgs [PATH:EXT] [OPTIONS]

description:
  Image-selection based on their exifdata.


positional argument:
  PATH                      All jpegs found under PATH will be regarded.
  EXT                       Look for files ending with EXT.


optional arguments:
  -h, --help                Print this help message and exit.
  -i, --info                Get some information about the images.
  -f, --format [FORMAT]     Specify the format of an index-file.
  -I, --index [FILE]   Use FILE as index instead of exif-data.
  -s, --sort TAG            Sort all images after TAG (if no exif-data available
                            for TAG the image will be excluded).
  -H, --headline           Print the output's format as first line.


arguments for image-selection:

  data:
  -d, --date DATE           Select all images captured at DATE.
  -t, --time TIME           Select all images captured at TIME.
  -e, --exposure-time SEC [SEC2]
                            Select all images whose exposure-time is SEC or
                            between SEC and SEC2.
  -m, --model [MODEL]       Select all images whose been made with MODEL.


  durations:
  -p, --plus [WEEKS] [DAYS] [HOURS] [MINUTES] [SECONDS]
                            Defines a duration that starts with a specified time.
  -a, --first-after         Select the first matched image for time-specific
                            selection.


  Use durations with --time or --time and --date to select all images of
  a specific duration.
"""


class Image:
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
    #TODO: couldn't I use just strings for datetime, date and time???
    def __init__(self, data):
        self._data = dict([(k, None) for k in self.ATTR])
        if type(data) == str: self.readexif(data)
        else:
            self._data.update(data)
            if self._data['date']:
                self._data['date'] = timeparser.parsedate(data['date'])
            if self._data['time']:
                self._data['time'] = timeparser.parsetime(data['time'])
            if self._data['exposure_time']:
                self._data['exposure_time'] = Fraction(data['exposure_time'])
            if self._data['datetime']:
                self._data['datetime'] = timeparser.parsedatetime(data['datetime'])

    def readexif(self, path):
        self._data['path'] = path
        self._data['name'] = os.path.basename(path)
        data = pyexiv2.ImageMetadata(path)
        data.read()
        def getvalue(key):
            try: return data[self.KEYS[key]].value
            except KeyError: return None
        datetime = getvalue('datetime')
        if datetime:
            self._data['datetime'] = datetime
            self._data['date'] = datetime.date()
            self._data['time'] = datetime.time()
        self._data['exposure_time'] = getvalue('exposure_time')
        self._data['model'] = getvalue('model')

    @classmethod
    def setformat(cls, fmt):
        for attr in Image.ATTR: fmt = fmt.replace(attr, '{' + attr + '}')
        cls.fmt = fmt

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


class Index:
    _format = None
    _sep = None
    def __init__(self, string):
        self._file = open(string, 'r')

    @property
    def file(self):
        return self._file

    @classmethod
    def setformat(cls, rawf):
        match = re.search('\W+', rawf)
        cls._sep = match.group() if match else ' '
        cls._format = re.findall('\w+', rawf)
        if not all([f in Image.ATTR for f in cls._format]):
            raise ValueError('{0} is not a valid format'.format(rawf))

    @property
    def format(self):
        if not self._format:
            self.file.seek(0)
            self.setformat(self.file.readline())
        return self._format

    @property
    def sep(self):
        return self._sep

    def __call__(self):
        self.format
        for line in self.file:
            yield dict(zip(self.format, line.split(self.sep)))


class Jexifs:
    def __init__(self, args):
        self.args = args
        self._images = list()
        self._selection = list()
        self._timed = dict()

    def run(self):
        if self.args.help: print HELP
        elif self.args.info: print len(self.images)
        else: self.printlines()

    @property
    def images(self):
        if self._images: return self._images
        if self.args.index: self._index()
        elif self.args.pathext: self._pathext()
        if self.args.sort: self._sort()
        return self._images

    def _index(self):
        #TODO: if not sorting this should be a generator!
        for data in self.args.index():
            self._images.append(Image(data))

    def _pathext(self):
        path, ext = self.args.pathext.split(':')
        for i,j,k in os.walk(path):
            for f in k:
                if not f.endswith(ext): continue
                self._images.append(Image(os.path.join(i, f)))
        #sort after paths if not sorting by option
        if not self.args.sort: self._images.sort(key=lambda i: i.path)

    def _sort(self):
        images = [i for i in self._images if getattr(i, self.args.sort)]
        images.sort(key=lambda i: getattr(i, self.args.sort))
        self._images = images

    def check_model(self, img):
        return self.args.model == img.model

    def check_exposure_time(self, img):
        exposure_time = self.args.exposure_time
        if len(exposure_time) == 1:
            return img.exposure_time == exposure_time[0]
        else:
            return exposure_time[0] < img.exposure_time < exposure_time[1]

    def check_dates(self, img):
        if not img.date: return False
        return any([date == img.date for date in self.args.date])

    @property
    def timed(self):
        if self._timed: return self._timed
        for time in self.args.time: self._timed[time] = False
        return self._timed

    def check_times(self, img):
        if not img.time: return False
        times = self.args.time
        if self.args.plus:
            if self.args.first_after:
                for time in times:
                    if self.timed[time]:
                        self.timed[time] = img.time > time
                    else:
                        self.timed[time] = img.time > time
                        if self.timed[time] and img.time < time + self.args.plus:
                            return True
                return False
            else:
                return any([t < img.time < t + self.args.plus for t in times])
        else:
            return any([t == img.time for t in times])

    def printlines(self):
        if self.args.headline: print Image.fmt.translate(None, '{}')
        for img in self.images:
            if self.args.time and not self.check_times(img): continue
            if self.args.date and not self.check_dates(img): continue
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
    '-i',
    '--info',
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
    '-I',
    '--index',
    type=Index,
    default=None
    )

parser.add_argument(
    '-d',
    '--date',
    action=timeparse.ParseDate,
    nargs='+',
    default=None
    )
parser.add_argument(
    '-t',
    '--time',
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
    )
parser.add_argument(
    '-a',
    '--first-after',
    action='store_true',
    )


def main():
    jexifs = Jexifs(parser.parse_args())
    timeparser.ENDIAN.set('big')
    try: jexifs.run()
    except Exception as err: raise


if __name__ == "__main__": main()


