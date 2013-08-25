jexifs
=========

Image-selection based on their exifdata.


Latest Version
--------------
The latest version of this project can be found at : http://github.com/thomst/jexifs.


Installation
------------
* Option 1 : Install via pip ::

    pip install jexifs

* Option 2 : If you have downloaded the source ::

    python setup.py install


Documentation
-------------
jexifs --help ::

    usage: 
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


Contribution
------------
Every kind of feedback is very welcome.


Reporting Bugs
--------------
Please report bugs at github issue tracker:
https://github.com/thomst/jexifs/issues


Author
------
thomst <thomaslfuss@gmx.de>
Thomas Leichtfuß

* http://github.com/thomst
