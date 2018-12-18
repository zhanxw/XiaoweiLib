from __future__ import print_function
import os, sys, re
try:
    from subprocess import Popen, PIPE, call
except:
    sys.path = [re.sub(r'^/home/zhanxw/', '/net/dumbo/home/zhanxw/', x) for x in sys.path]
    sys.path.append('/net/dumbo/home/zhanxw/python27/lib/python2.7/')
    from subprocess import Popen, PIPE, call

from multiprocessing import Pool
import gzip
import signal

def myopen(fn):
    import gzip
    f = gzip.open(fn)
    try:
        f.read(2)
        f.close()
        return gzip.open(fn)
    except:
        f.close()
        return open(fn)

from subprocess import CalledProcessError
class CalledProcessTimeOutError(CalledProcessError):
    """This exception is raised when a process run by mycheck_output() returns a non-zero exit status.
    The exit status will be stored in the returncode attribute;
    check_output() will also store the output in the output attribute.
    """
    def __init__(self, returncode, cmd, output=None):
        self.returncode = returncode
        self.cmd = cmd
        self.output = output
    def __str__(self):
        return "Command '%s' returned non-zero exit status %d" % (self.cmd, self.returncode)

def printTotalThread():
    import threading
    for t in threading.enumerate():
        print ('thread = ', t)
        
def mycheck_output(*popenargs, **kwargs):
    if 'timeOut' not in kwargs:
        ## print "timeOut is None"
        from subprocess import check_output
        return check_output(*popenargs, **kwargs)
    try:
        timeOut = kwargs['timeOut']
        del kwargs['timeOut']
        timeOut = int(timeOut)
    except:
        print ("Time out is not an integer", timeOut, file = sys.stderr)
        return None
    
    import subprocess, threading
    class Command(object):
        def __init__(self, *cmd, **kwargs):
            self.cmd = cmd
            self.kwargs = kwargs
            self.process = None
            self.output = ''
            self.terminated = False
            # print 'cmd = ', self.cmd
            # print 'args = ', self.kwargs

        def run(self, timeOut):
            ## print "run() - ", self.cmd
            def target():
                # print 'Thread started'
                # print 'cmd = ', self.cmd
                # print 'args = ', self.kwargs
                ## Popen will immediately return, but we can check its status later
                self.process = subprocess.Popen(stdout = PIPE, *self.cmd, **self.kwargs)
                
                ## sleep more time than timeOut so the thread is not stopped before we
                ## check process status
                from time import sleep
                sleep(0.1)

                # print self.cmd, self.kwargs
                # print 'Thread finished'

            thread = threading.Thread(target=target, name = "worker")
            thread.start()
            thread.join(timeOut)
            if thread.is_alive():
                
                if self.process.poll() == None:
                    #print "still running", self.process.pid
                    self.process.terminate()
                    self.terminated = True

                    cmd = self.kwargs.get("args")
                    if cmd is None:
                        cmd = popenargs[0]
                    thread.join()
                    raise CalledProcessTimeOutError(self.process.returncode, cmd, output=self.output )
                else:
                    #print "process is done"
                    self.terminate = False
                

            ### self.output, unused_err = self.process.communicate()
            ## print "thread join...."
            thread.join()
            ## print "command finish normally"

            #if self.process.returncode != None:
                # print "read communicate result"
                #self.output, unused_err = self.process.communicate()
            # print self.process
            # print self.process.returncode
            self.output, unused_err = self.process.communicate()
            # else:
            #   print "skip read communicate result"
                
            return self.output

            
    command = Command(*popenargs, **kwargs)
    return command.run(timeOut = timeOut)
    
# this should be replaced by 'glob'
# files = getFileList("*BS_SE*sam")
def getFileList(filter=None, recursive=False):
    import fnmatch
    if (recursive == False):
        p1 = Popen("ls -l --color=none -1 ".split() , shell=True, stdout=PIPE)
    else:
        p1 = Popen("find .".split() , stdout=PIPE)
    output = p1.communicate()[0].splitlines()
    if (filter == None):
        return output
    return fnmatch.filter(output, filter)

# create dir, not warn if path preexists
def safeMkdir(path): 
    try:
        os.mkdir(path)
    except OSError:
        pass

# get SM tag from BAM file header
def getSMTag(fn):
    from subprocess import check_output
    pat = re.compile(r'SM:(\b)')

    smTag = '' # keep last SM tag
    #print fn
    o = check_output( ("samtools view -H %s" % fn).split()).split('\n')
    o = filter(lambda x: pat.search(x) != None , o)
    o = [ln for ln in o if ln[:3] == '@RG']
    if len(o) != 1:
        print ("%s has multiple tags!!" % fn, file = sys.stderr)
    for ln in o:
        #print 'ln=', ln
        for x in ln.split('\t'):
            #print 'x=', x
            if x.find('SM')>=0:
                if smTag == '':
                    smTag = x[3:]
                    #print "%s\t%s" % (fn, x[3:])
                else:
                    if smTag[3:] != x[3:]:
                        print ("%s has multiple CONFLICT tags (comparing to %s)!" % (smTag, x[3:]), file = sys.stderr)
                        print (smTag, file = sys.stderr)
    # if smTag == '':
    #   print "%s\tNA" % fn
    return smTag

""" Change file suffix (if there is not suffix, then manual add one)"""
def changeSuffix(fileName,newSuffix):
    dotPosition=fileName.rfind(".")
    if (dotPosition < 0):
        return (fileName+"."+newSuffix)
    return ( fileName[:(dotPosition+1)] + newSuffix )

# check if file name has any suffix in the suffixLists
# e.g. checkSuffix("abc.ss", ("s","ss") 
def checkSuffix(fileName, suffixLists):
    dotPosition=fileName.rfind(".")
    if (dotPosition < 0):
        return False
    if (isinstance(suffixLists, type("")) == True):
        return (fileName[dotPosition+1 : ] == suffixLists)
    for s in suffixLists:
        if (fileName[dotPosition+1 :] == s):
            return True
    return False

# region is a dict(): key chrom, val: list of ranges
# ranges: [ [1,2], [5, 10]...]
# return merged results as a new dict
def mergeRegion(region):
    for chrom in region.iterkeys():
        ex = region[chrom]
        ex.sort(key = lambda x: x[0])

        ret = []
        for i, r in enumerate(ex):
            if len(ret) == 0:
                ret.append(r)
                continue
            last_end = ret[-1][1]
            beg = r[0]
            end = r[1]
            if beg < last_end:
                if end > last_end:
                    ret[-1][1] = end
            else:
                ret.append(r)
        region[chrom] = ret
    return region

class BedFile:
    def __init__(self):
        self.data = dict()
    # return len of chroms and total bases
    def open(self, fn, trimChrPrefix = False):
        for ln in myopen(fn):
            fd = ln.strip().split()
            chrom, beg, end = fd[:3]
            if chrom[:3].lower() == 'chr':
                if trimChrPrefix:
                    chrom = chrom[3:]
                else:
                    print ("Be cautious of 'chr' as chromosome prefix", file = sys.stderr)
            beg, end = int(beg), int(end)
            if chrom in self.data:
                self.data[chrom].append( [beg, end] )
            else:
                self.data[chrom] = [ [beg, end] ]
        self.data = mergeRegion(self.data)
        return len(self.data), sum( (len(self.data[chrom]) for chrom in self.data.iterkeys())) 
    # boundary is left inclusive, right exclusive.
    def contain(self, chrom, pos):
        if chrom not in self.data:
            return False
        try:
            pos = int(pos)
        except:
            return False
        region = self.data[chrom]
        lo = 0
        hi = len(region)
        while lo < hi:
            mid = (lo + hi) /2
            midval = region[mid]
            if pos < midval[0]:
                hi = mid
            elif midval[0] <= pos < midval[1]:
                return True
            elif pos >= midval[1]:
                lo = mid + 1
        return False
    # return a tuple ( a, b, c) where
    # a: whether chrom:pos is contained
    # (b, c): if a == True, get region
    #         if a == False, get distance to left and distance to right
    # e.g.  region: [100, 200), [300,400)
    # return (True, 100, 200) if call getDistance(chrom, 150)
    # return (False, 1, 99) if call getDistance(chrom, 201)
    def getDistance(self, chrom, pos):
        if chrom not in self.data:
            return False
        try:
            pos = int(pos)
        except:
            return (False, None, None)
        region = self.data[chrom]
        lo = 0
        hi = len(region)
        mid = None
        if hi == 0: 
            return (False, None, None)
        while lo < hi:
            mid = (lo + hi) /2
            midval = region[mid]
            if pos < midval[0]:
                hi = mid
            elif midval[0] <= pos < midval[1]:
                return (True, midval[0], midval[1])
            elif pos >= midval[1]:
                lo = mid + 1
        if mid == 0:
            midval = regin[mid]
            
        elif mid == len(region) - 1:
            midval = regin[mid]
        else:
            midval = regin[mid]

        return False

# .fai format
# contig, size, location, basesPerLine, bytesPerLine
# e.g.
# 1       249250621       52      60      61
# 2       243199373       253404903       60      61
class GenomeSequence:
    gs = None
    def __init__(self):
        pass
    def isGzFile(self, fn):
        try:
            with open(fn) as f:
                GZMagicNumber = '\x1f\x8b\x08'
                if f.read(3) == GZMagicNumber:
                    return True
        except:
            pass
        return False
    #' Check if it is plain .fa file
    def isPlainFile(self, fn):
        try:
            with open(fn) as f:
                if f.read(1) == ">":
                    return True
        except:
            pass
        return False
    # return number of chromosomes loaded
    def open(self, fn):
        if not os.path.exists(fn):
            print ("Reference genome file does not exist: " + fn, file = sys.stderr)
            return -1
        
        # check if .fai file exists
        if os.path.exists(fn + '.fai') or os.path.exists(fn.replace('.gz', '') + '.fai'):
            # check if fn is a gzip file
            if self.isGzFile(fn):
                self.gs = BgzipIndexedGenomeSequence()
            elif self.isPlainFile(fn):
                self.gs = PlainIndexedGenomeSeqeunce()
            else:
                print ("Unsupported genome sequence type!", file = sys.stderr)
                return -1
        else:
            self.gs = InMemoryGenomeSequence()
        return self.gs.open(fn)
    def read(self, fn):
        return self.gs.open(fn)
    # pos: 0-based index
    def getBase0(self, chrom, pos):
        return self.gs.getBase0(chrom, pos)
    # pos: 1-based index
    def getBase1(self, chrom, pos):
        return self.gs.getBase1(chrom, pos)

# Genome sequence is xxx.fa or xxx.fa.gz, but does not have the .fai index        
class InMemoryGenomeSequence:
    gs = dict()
    def __init__(self):
        pass
    def open(self, fn):
        content = [ln.strip() for ln in myopen(fn).readlines() if len(ln.strip()) > 0 ]
        chromIdx = [i for i, ln in enumerate(content) if ln[0] == '>' ]
        chroms = [content[i][1:].split()[0].replace('chr', '') for i in chromIdx]
        seqIdx = [ (chromIdx[i], chromIdx[i+1]) for i in xrange(len(chromIdx) - 1) ]
        seqIdx.append( (chromIdx[-1], len(content) ) )
        seq = [ ''.join(content[ ( i[0] + 1) : i[1]]) for i in seqIdx]
        self.gs = dict(zip(chroms, seq))
        for k, v in self.gs.iteritems():
            print ("Chromosome %s loaded with %d bases" % (k, len(v)), file = sys.stderr)
        return len(self.gs)
    def read(self, fn):
        return self.open(fn)
    # pos: 0-based index
    def getBase0(self, chrom, pos):
        chrom = chrom.replace('chr','')
        pos = int(pos)
        if chrom not in self.gs:
            return 'N'
        return self.gs[chrom][pos]
    # pos: 1-based index
    def getBase1(self, chrom, pos):
        chrom = chrom.replace('chr','')
        pos = int(pos)
        if chrom not in self.gs:
            return 'N'
        return self.gs[chrom][pos - 1]

## Sequence file is xxx.fa, and has an index file xxx.fa.fai
class PlainIndexedGenomeSeqeunce:
    handle = None
    index = {}
    def __init__(self):
        pass
    def open(self, fn):
        self.handle = open(fn, 'r')
        # read fai
        for ln in myopen(fn + '.fai'):
            fd = ln.strip().split()
            self.index[fd[0].replace('chr', '')] = [int(i) for i in fd[1:]]
        return len(self.index)            
    def read(self,fn):
        return self.open(fn)
    def getBase0(self, chrom, pos):
        chrom = chrom.replace('chr','')
        if chrom not in self.index:
            return 'N'
        chromLen, fileOffset, nchar, nchar2 = self.index[chrom]
        if pos >= chromLen or pos < 0:
            return 'N'
        a, b = divmod(pos, nchar)
        offset = fileOffset + a * nchar2 + b
        self.handle.seek(offset)
        return self.handle.read(1)

    # pos: 1-based index
    def getBase1(self, chrom, pos):
        return self.getBase0(chrom, pos - 1)

## Sequence file is xxx.fa.gz, and has an index file xxx.fa.gz.fai (or xxx.fa.fai)
class BgzipIndexedGenomeSequence:
    handle = None
    voffset = []  # store virtual offsets [raw_start, raw_len, data_start, data_len]
    vdataOffset = []
    vidx = None
    index = {}
    def __init__(self):
        try:
            from Bio import bgzf
        except:
            print ("Cannot import Bio.bgzf, need to check the installation", file = sys.stderr)
        pass
    def open(self, fn):
        from Bio import bgzf        
        self.handle = bgzf.BgzfReader(fn)
        # read bgzf blocks
        from time import ctime

        self.voffset = self.computeBgzfBlocks(fn)
        # with open(fn) as f:
        #     for v in bgzf.BgzfBlocks(f):
        #         self.voffset.append(v)
        self.vdataOffset = [i[2] for i in self.voffset]
        # read fai
        if os.path.exists(fn + '.fai'):
            indexFilename = fn + '.fai'
        elif os.path.exists(fn.replace('.gz', '') + '.fai'):
            indexFilename = fn.replace('.gz', '') + '.fai'
        else:
            indexFilename = None
        for ln in myopen(indexFilename):
            fd = ln.strip().split()
            self.index[fd[0].replace('chr', '')] = [int(i) for i in fd[1:]]
        return len(self.index)
    # a quick way to get bgzf blocks
    # similar to Bio.bgzf.BgzfBlocks()
    # return [(raw start, raw length, data start, data length)...]
    # refer to the BGZF specification at:
    # https://samtools.github.io/hts-specs/SAMv1.pdf
    def computeBgzfBlocks(self, fn):
        import struct
        blocks = []
        f = open(fn, 'rb')
        poffset = 0 # physical offset
        doffset = 0 # data offset (in uncompressed data)
        while True:
          f.seek(poffset, 0)
          id1, id2, cm, flg, mtime, xfl, os, xlen = struct.unpack('<BBBBIBBH', f.read(12))
          assert xlen == 6
          si1, si2, slen, bsize = struct.unpack('<BBHH', f.read(6))
          f.seek(poffset + bsize + 1 - 4, 0)
          isize = struct.unpack('<I', f.read(4))[0]
          v = (poffset, bsize + 1, doffset, isize)
          # print >> fout, v
          blocks.append( v )

          poffset += bsize + 1
          doffset += isize

          if  not f.read(1): # reach the file end
              break
        #print blocks
        return blocks
    # seek to the virtual_offset in the bgzf file (dataOffset is the offset for uncompressed data)
    def seekToPosition(self, dataOffset):
        from Bio import bgzf        
        # binary search
        from bisect import bisect_right
        lo = 0
        if self.vidx != None and self.vdataOffset[self.vidx] < dataOffset:
            lo = self.vidx
        hi = len(self.vdataOffset)
        if self.vidx != None and lo + 50 < len(self.vdataOffset) and self.vdataOffset[self.vidx+50] > dataOffset:
            hi = self.vidx + 50
        self.vidx = bisect_right(self.vdataOffset, dataOffset, lo = lo, hi = hi)
        self.vidx -= 1
        # print self.vidx
        # need to first get virtual offset of BGZF
        vo = bgzf.make_virtual_offset(self.voffset[self.vidx][0], dataOffset - self.vdataOffset[self.vidx])
        self.handle.seek(vo)
    def read(self,fn):
        return self.open(fn)
    def getBase0(self, chrom, pos):
        chrom = chrom.replace('chr','')
        if chrom not in self.index:
            return 'N'
        chromLen, fileOffset, nchar, nchar2 = self.index[chrom]
        if pos >= chromLen or pos < 0:
            return 'N'
        a, b = divmod(pos, nchar)
        offset = fileOffset + a * nchar2 + b
        self.seekToPosition(offset)
        return self.handle.read(1)
    # pos: 1-based index
    def getBase1(self, chrom, pos):
        return self.getBase0(chrom, pos - 1)

def run(cmd):
    print("= %s" % cmd)
    if (cmd.find(">") <0 ):     # no need to redirect output
        call(cmd.split())
        return
    else:
        p=Popen(cmd, shell=True)
        os.waitpid(p.pid, 0)
        return

def runPool(cmdList, poolSize=4):
    pool = Pool(processes = poolSize)
    pool.map(run, cmdList)

def fastCompressGzip(fn):
    import subprocess
    p = subprocess.Popen(["gzip", "-c", fn], stdout = subprocess.PIPE, close_fds=True, universal_newlines = False)
    return p.stdout

def fastDecompressGzip(fn):
    import subprocess
    p = subprocess.Popen(["zcat", fn], stdout = subprocess.PIPE, close_fds = False, universal_newlines = False)
    return p.stdout
    
"""iterator help you get a list with four elements of any FASTQ record"""
class FastqReader:
    def __init__(self, fileName):
        if (len(fileName)>3 and fileName[-3:]==".gz"):
            self.f = gzip.open(fileName, "rb")
        else:
            self.f = open(fileName)
        signal.signal(signal.SIGPIPE, signal.SIG_DFL) 

    def __iter__(self):
        return self

    def next(self):
        record = [ self.f.readline().strip() for i in range(4)]
        if (record[0] == ''):
            self.f.close()
            raise StopIteration
        return record

class SAMReader:
    def __init__(self, fileName, isBam = False):
        if (isBam == False and fileName[-4:] == ".sam"):
            self.f = open(fileName)
        elif (isBam == True and fileName[-4:] == ".bam"):
            args = "samtools view " + fileName
            print (args.split())
            self.f = Popen( args.split(), stdout=PIPE).stdout
        else:
            print("your suffix and does not match value self.isBam")
            sys.exit(1)
        self.header = list() # store SAM header
        self.lineNo = 0 # store current read line number
        self.line = "" # store current read line
        signal.signal(signal.SIGPIPE, signal.SIG_DFL) 
        
    def __iter__(self):
        return self
    def next(self):
        self.line = self.f.readline()
        self.lineNo += 1
        while (self.line != '' and self.line[0] == '@'):
            self.header.append(self.line)
            self.line = self.f.readline()
            self.lineNo += 1

        if (self.line == ''):
            self.f.close()
            raise StopIteration

        fields= self.line.split('\t')
        record = dict()
        record["QNAME"] = fields[0]
        record["FLAG" ] = int(fields[1])
        record["RNAME"] = fields[2]
        record["POS"  ] = int(fields[3])
        record["MAPQ" ] = int(fields[4])
        record["CIGAR"] = fields[5]
        record["MRNM" ] = fields[6]
        record["MPOS" ] = int(fields[7])
        record["ISIZE"] = int(fields[8])
        record["SEQ"  ] = fields[9]
        record["QUAL" ] = fields[10]
        record["TAGS" ] = fields[11:]

# we don't care the optional tags unless necessary
#         if (len(fields) > 11):
#             for i in fields[11:]:
#                 (tag, vtype, value) = i.split(":")
#                 if (vtype=="i"):
#                     record[tag] = int(value)
#                 elif(vtype=="f"):
#                     record[tag] = float(value)
#                 else:
#                     record[tag] = value
        return record

    def dump(self):
        print (self.line)

# from Dive into Python
def info(object, spacing=10, collapse=1):   
    """Print methods and doc strings.
    
    Takes module, class, list, dictionary, or string."""
    methodList = [method for method in dir(object) if callable(getattr(object, method))]
    processFunc = collapse and (lambda s: " ".join(s.split())) or (lambda s: s)
    print ("\n".join(["%s %s" %
                      (method.ljust(spacing),
                       processFunc(str(getattr(object, method).__doc__)))
                     for method in methodList]))


#import __main__ # will access the global variables set in __main__
# e.g. Note, you need to put code under __main__ 
#     boolParam = False
#     intParam = 1
#     floatParam = 2.3
#     strParam = "empty"

#     getOptClass = GetOptClass()
#     argumentList = (
#         ('boolParam', ('-b','--bool')),
#         ('intParam',  ('-i', '--integer')),
#         ('floatParam',  ('-f', '--float')),
#         ('strParam', ('-s', '--str'))
#         )
#     getOptClass.parse(argumentList, verbose= False )
#     print 'boolParam = ', boolParam
#     print 'intParam = ', intParam
#     print 'floatParam = ', floatParam
#     print 'strParam = ', strParam
#     print 'rest arguments = ', ",".join(getOptClass.rest)

class InMemoryGenomeSequence:
    gs = dict()
    def __init__(self):
        pass
    def open(self, fn):
        content = [ln.strip() for ln in open(fn).xreadlines() if len(ln.strip()) > 0 ]
        chromIdx = [i for i, ln in enumerate(content) if ln[0] == '>' ]
        chroms = [content[i][1:].split()[0] for i in chromIdx]
        seqIdx = [ (chromIdx[i], chromIdx[i+1]) for i in xrange(len(chromIdx) - 1) ]
        seqIdx.append( (chromIdx[-1], len(content) ) )
        seq = [ ''.join(content[ ( i[0] + 1) : i[1]]) for i in seqIdx]
        self.gs = dict(zip(chroms, seq))
        # for k, v in self.gs.iteritems():
        #     print >> sys.stderr, "Chromosome %s loaded with %d bases" % (k, len(v))
        return len(self.gs)
    def read(self, fn):
        return self.open(fn)
    # pos: 0-based index
    def getBase0(self, chrom, pos):
        chrom = chrom.replace('chr','')
        if chrom not in self.gs:
            return 'N'
        return self.gs[chrom][pos]

    # pos: 1-based index
    def getBase1(self, chrom, pos):
        chrom = chrom.replace('chr','')
        if chrom not in self.gs:
            return 'N'
        return self.gs[chrom][pos - 1]

class GetOptClass:
    rest = []
    def __init__(self):
        pass
    def parse(self, optList, verbose=False):
        # assigne default values should be finished outside of this class
        # preprocess argument
        optDict = dict()
        for i in optList:
            for j in i[1]:
                if len(j) == 0 or j[0] != '-':
                    print ("Illegal options: %s" % j)
                    sys.exit(1)
                optDict[j] = i[0]

        # parse sys.argv
        index = 1
        while index < len(sys.argv):
            opt = sys.argv[index]
            if opt in optDict:
                # assign the parameter
                varName = optDict[opt]
                # detect if the parameter is bool
                isBoolType = False
                exec('isBoolType = False.__class__ == __main__.%s.__class__' % varName )
                #print isBoolType
                if (isBoolType):
                    try:
                        exec("__main__.%s = True" % varName ) 
                    except:
                        print ("Cannot set the boolean variable: %s" % varName)
                else:
                    try:
                        arg = sys.argv[index+1]
                    except:
                        print ("Not provided argument for option: %s" % varName)
                    try:
                        exec("__main__.%s = (__main__.%s.__class__)(%s)" % (varName, varName, repr(arg)))
                    except:
                        print ("Cannot set the boolean variable: %s" % varName)
                    index += 1
            else:
                self.rest.append(opt)

            index += 1
        
        #check result
        if (verbose == True):
            self.dump(optList, optDict)
        
    def dump(self, optList, optDict):
        print ("%s by Xiaowei Zhan" % sys.argv[0])
        print ()
        print ("User Specified Options")
        for i in optList:
            try:
                print ((",".join(i[1])).rjust(20),':', end = '')
                exec ("print %s " % optDict[i[1][0]])
            except:
                print ("Failed to dump ", i)
                raise
        print ('rest arguments'.rjust(20), ':', ",".join(self.rest))

# from Dabeaz's great slides
import os 
import fnmatch
def gen_find(filepat,top): 
    for path, dirlist, filelist in os.walk(top):
        for name in fnmatch.filter(filelist,filepat): 
            yield os.path.join(path,name)

import gzip, bz2 
def gen_open(filenames):
    for name in filenames: 
        if name.endswith(".gz"):
            yield gzip.open(name) 
        elif name.endswith(".bz2"):
            yield bz2.BZ2File(name) 
        else:
            yield open(name)

def gen_cat(sources): 
    for s in sources:
        for item in s: 
            yield item

def gen_grep(pat, lines): 
    patc = re.compile(pat) 
    for line in lines:
        if patc.search(line): 
            yield line

## copy from Tabix
import sys
from ctypes import *
from ctypes.util import find_library
import glob, platform

def load_shared_library(lib, _path='.', ver='*'):
    """Search for and load the tabix library. The
    expectation is that the library is located in
    the current directory (ie. "./")
    """
    # find from the system path
    path = find_library(lib)
    if (path == None): # if fail, search in the custom directory
        s = platform.system()
        if (s == 'Darwin'): suf = ver+'.dylib'
        elif (s == 'Linux'): suf = '.so'+ver
        candidates = glob.glob(_path+'/lib'+lib+suf);
        if (len(candidates) == 1): path = candidates[0]
        else: return None
    cdll.LoadLibrary(path)
    return CDLL(path)
def tabix_init():
    """Initialize and return a tabix reader object
    for subsequent tabix_get() calls.  
    """
    tabix = load_shared_library('tabix', "/net/wonderland/home/zhanxw/mydata/dbSNP/snp137.db/") ## HARD CODE PATH HERE
    if (tabix == None): return None
    tabix.ti_read.restype = c_char_p
    # on Mac OS X 10.6, the following declarations are required.
    tabix.ti_open.restype = c_void_p
    tabix.ti_querys.argtypes = [c_void_p, c_char_p]
    tabix.ti_querys.restype = c_void_p
    tabix.ti_query.argtypes = [c_void_p, c_char_p, c_int, c_int]
    tabix.ti_query.restype = c_void_p
    tabix.ti_read.argtypes = [c_void_p, c_void_p, c_void_p]
    tabix.ti_iter_destroy.argtypes = [c_void_p]
    tabix.ti_close.argtypes = [c_void_p]
    # FIXME: explicit declarations for APIs not used in this script
    return tabix
# OOP interface
class Tabix:
    def __init__(self, fn, fnidx=0):
        self.tabix = tabix_init();
        if (self.tabix == None):
            sys.stderr.write("[Tabix] Please make sure the shared library is compiled and available.\n")
            return
        self.fp = self.tabix.ti_open(fn, fnidx);

    def __del__(self):
        if (self.tabix): self.tabix.ti_close(self.fp)

    def fetch(self, chr, start=-1, end=-1):
        """Generator function that will yield each interval
        within the requested range from the requested file.
        """
        if (self.tabix == None): return
        if (start < 0): iter = self.tabix.ti_querys(self.fp, chr) # chr looks like: "chr2:1,000-2,000" or "chr2"
        else: iter = self.tabix.ti_query(self.fp, chr, start, end) # chr must be a sequence name
        if (iter == None):        
            sys.stderr.write("[Tabix] Malformatted query or wrong sequence name.\n")
            return
        while (1): # iterate
            s = self.tabix.ti_read(self.fp, iter, 0)
            if (s == None): break
            yield s   
        self.tabix.ti_iter_destroy(iter)

class TabixReader:
    def __init__(self, fn, _range):
        self.tabix = Tabix(fn)
        self.r = _range
        self.gen = self.tabix.fetch(self.r)
    def readline(self):
        try:
            ln = self.gen.next()
            return ln
        except StopIteration:
            return ""
# read an class has readline() function
def tabixOpen(fn, _range):
    return TabixReader(fn, _range)

# group n element together
# http://stackoverflow.com/questions/4998427/how-to-group-elements-in-python-by-n-elements
def grouper(n, iterable, fillvalue=None):
    "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    from itertools import izip_longest
    return izip_longest(fillvalue=fillvalue, *args)

# flatten a list of list (@param list2d)to a list
# from http://stackoverflow.com/questions/952914/making-a-flat-list-out-of-list-of-lists-in-python
def flatten2d(list2d):
    from itertools import chain
    return list(chain(*list2d))

# recursively flatten a list @param x
# from: http://stackoverflow.com/questions/2158395/flatten-an-irregular-list-of-lists-in-python
def flatten(x):
    import collections
    if isinstance(x, collections.Iterable):
        return [a for i in x for a in flatten(i)]
    else:
        return [x]

# get chunks of lists
# http://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks-in-python
def makeChunk(l, n):
    """Yield successive n-sized chunks from l."""
    for i in xrange(0, len(l), n):
       yield l[i:i+n]


