# https://packaging.python.org/tutorials/packaging-projects/#packaging-your-project
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name = "XiaoweiLib",
    version = "1.2.8",
    author = "Xiaowei Zhan",
    author_email = "zhanxw@gmail.com",
    description = "Common codes used by Xiaowei",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url = "https://github.com/zhanxw/XiaoweiLib",
    # do NOT use packages, as this is a module only package,
    # otherwise, packages= create __init__.py and messed the namespaces
    #packages=setuptools.find_packages(), 
    classifiers = [
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Development Status :: 4 - Beta",
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development :: Testing",
        ],
    
    py_modules=['OrderedSet',
        'PrettyTable',
        'XiaoweiJob',
        'XiaoweiLib',
        'XiaoweiTask'],
    keywords = ["zhanxw", "library", "python", "utility"],
)
