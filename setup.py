from distutils.core import setup
import os

VERSION = "0.3.0"

setup( 
    name = "jexifs", 
    version = VERSION, 
    author = "Thomas Leichtfuss", 
    author_email = "thomaslfuss@gmx.de",
    url = "https://github.com/thomst/jexifs",
    download_url = "https://pypi.python.org/packages/source/j/jexifs/jexifs-{version}.tar.gz".format(version=VERSION),
    description = 'Select jpegs based on their exif-data.',
    long_description = open('README.rst').read() if os.path.isfile('README.rst') else str(),
    py_modules = ["jexifs"],
    scripts = ["jexifs"],
    install_requires = ['timeparse', 'timeparser'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.7',
        'Topic :: Utilities',
    ],
    license='GPL',
    keywords='exif exifdata jpeg time batch selection',
)
