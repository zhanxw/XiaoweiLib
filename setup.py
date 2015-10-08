# chardet's setup.py
from distutils.core import setup
setup(
    name = "XiaoweiLib",
    # https://docs.python.org/2/distutils/examples.html
    py_modules=['OrderedSet',
        'PrettyTable',
        'XiaoweiJob',
        'XiaoweiLib',
        'XiaoweiTask'],
    #packages = ['XiaoweiLib'],
    version = "1.1",
    description = "Common codes used by Xiaowei",
    author = "Xiaowei Zhan",
    author_email = "zhanxw@gmail.com",
    url = "https://github.com/zhanxw/XiaoweiLib",
    download_url = "https://pypi.python.org/pypi/XiaoweiLib",
    keywords = ["zhanxw", "library", "python", "utility"],
    classifiers = [
        "Programming Language :: Python",
	"Programming Language :: Python :: 2",
        "Development Status :: 4 - Beta",
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
	"Intended Audience :: Science/Research",
	"License :: OSI Approved :: GNU General Public License (GPL)",
        "Operating System :: OS Independent",
	"Topic :: Scientific/Engineering",
        "Topic :: Software Development :: Testing",
	"Topic :: System :: Monitoring",
        ],
    long_description = """\
Common Codes Used by Xiaowei
-------------------------------------

Please read source codes.

Contact
-------

  Xiaowei Zhan<zhanxw[at]gmail.com>
  
"""
)
