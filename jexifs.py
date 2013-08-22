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
import fractions
import timeparse
import timeparser
import daytime
from datetime import datetime
from datetime import time
from datetime import timedelta
from datetime import date

timeparser.TimeFormats.config(try_hard=True)
timeparser.DateFormats.config(try_hard=True)
timeparser.DatetimeFormats.config(try_hard=True)


LABEL_KEYS = {
    'Canon' : {
        'model' : 'Exif.Image.Model',
        'datetime' : 'Exif.Image.DateTime',
        'exposure_time' : 'Exif.Photo.ExposureTime',
        },
    }


class Image:
    def __init__(self, path=None, name=None, date=None, time=None, exposure_time=None, model=None):
        self._name = name
        self._path = path
        #timeparsers try_hard-option should built formats for all endian-options
        timeparser.ENDIAN.set('big')
        self._date = date and timeparser.parsedate(date)
        timeparser.ENDIAN.set()
        self._time = time and daytime.DayTime(timeparser.parsetime(time))
        self._exposure_time = exposure_time and fractions.Fraction(exposure_time)
        self._model = model
        self._dict = None
        self._datetime = None
        self._data = None

    def _get_key(self, tag):
        return LABEL_KEYS['Canon'][tag]

    @property
    def path(self):
        return self._path

    @property
    def name(self):
        return os.path.basename(self._path)

    @property
    def data(self):
        if not self._data:
            self._data = pyexiv2.ImageMetadata(self.path)
            self._data.read()
        return self._data

    @property
    def datetime(self):
        if not self._datetime:
            key = self._get_key('datetime')
            try: self._datetime = self.data[key].value
            except KeyError: self._datetime = None
        return self._datetime

    @property
    def date(self):
        if not self._date:
            if not self.datetime: self._date = None
            else: self._date = self.datetime.date()
        return self._date

    @property
    def time(self):
        if not self._time:
            if not self.datetime: self._time = None
            else: self._time = self.datetime.time()
        return self._time

    @property
    def exposure_time(self):
        key = self._get_key('exposure_time')
        try: return self.data[key].value
        except KeyError: return None

    @property
    def model(self):
        key = self._get_key('model')
        try: return self.data[key].value
        except KeyError: return None

    @property
    def dict(self):
        if not self._dict:
            self._dict = dict(
                name=self.name,
                path=self.path,
                model=self.model,
                date=self.date,
                time=self.time,
                datetime=self.datetime,
                exposure_time=self.exposure_time
                )
        return self._dict



class Index:
    def __init__(self, fileobj, sep=' ', format=None):
        self._fileobj = fileobj
        self._sep = sep
        self._format = format
        self._data

    @property
    def fileobj(self):
        return self._fileobj

    @property
    def format(self):
        if not self._format:
            self.fileobj.seek(0)
            self._format = self.file.readline().split(self.sep)
        return self._format

    @property
    def sep(self):
        return self._sep

    @property
    def data(self):
        if not self._data:
            fmt = self.format   #be sure first line was already read
            for line in self.fileobj.readlines:
                self._data.append(dict(zip(fmt, line.split(self.sep))))
            self._data = self.fileobj.readlines



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
  -r, --read-index [FILE]   Use FILE as index instead of exif-data.
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
    nargs='?',
    default='{name} {date} {time}',
    )
parser.add_argument(
    '-r',
    '--read-index',
    type=argparse.FileType('r'),
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
    type=fractions.Fraction,
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


class Jexifs:
    def __init__(self, args):
        self.args = args
        self._images = list()
        self._selection = list()
        self._timed = dict()


    @property
    def images(self):
        if self._images: return self._images
        if self.args.read_index: self._read_index()
        elif self.args.pathext: self._pathext()
        if self.args.sort: self._sort()
        return self._images

    def _read_index(self):
        index = Index(self.args.read_index)
        for data in index.data:
            self._images.append(Image(**data))

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

    @property
    def selection(self):
        if self._selection: return self._selection
        for img in self.images:
            if not self.check_model(img): continue
            if not self.check_exposure_time(img): continue
            if not self.check_times(img): continue
            if not self.check_dates(img): continue
            self._selection.append(img)
        return self._selection

    def check_model(self, img):
        if not self.args.model: return True
        else: return self.args.model == img.model

    def check_exposure_time(self, img):
        exposure_time = self.args.exposure_time
        if not exposure_time:
            return True
        elif len(exposure_time) == 1:
            return img.exposure_time == exposure_time[0]
        else:
            return exposure_time[0] < img.exposure_time < exposure_time[1]

    def check_dates(self, img):
        if not self.args.date: return True
        elif not img.date: return False
        return any([date == img.date for date in self.args.date])

    @property
    def timed(self):
        if self._timed: return self._timed
        for time in self.args.time: self._timed[time] = False
        return self._timed

    def check_times(self, img):
        if not self.args.time: return True
        elif not img.time: return False
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

    def run(self):
        if self.args.help: print HELP
        elif self.args.info: print len(self.images)
        else: self.printlines()

    def printlines(self):
        if self.args.headline: print self.args.format.translate(None, '{}')
        if not any((self.args.date, self.args.time, self.args.exposure_time, self.args.model)):
            for img in self.images: print self.args.format.format(**img.dict)
        else:
            for img in self.selection: print self.args.format.format(**img.dict)


if __name__ == "__main__":
    jexifs = Jexifs(parser.parse_args())
    try: jexifs.run()
    except Exception as err: raise


