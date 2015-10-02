import sys, os
import time
import subprocess

deltaIndent = 10
tab= '\-----'.rjust(deltaIndent)

class JobSet:
    """
    class JobSet may contain JobSet or Job
    status: U - "unstart / unsuccessfully finished", R - "running", F - "finished"
    """
    def __init__(self, tag=""):
        self.tag = tag
        self.content = list()
    def append(self, job):
        if (isinstance(job, JobSet) or isinstance(job, Job)):
            self.content.append(job)
        elif (isinstance(job, list) or isinstance(job, tuple)):
            for i in job:
                self.content.append(Job(i))
        else:
            raise
    def getJob(self):
        for i in self.content:
            j = i.getJob()
            if j != None:
                return j
        return None
    def dump(self, indent = 0 ):
        if (indent >= deltaIndent):
            print ''.ljust(indent-deltaIndent),
            print tab, "*%s" % self.tag

        else:
            print "*%s" % self.tag
        length = len(self.content)
        for i in range(length):
            self.content[i].dump(indent+deltaIndent)

class Job:
    """ each Job is a command with its running status ('U', 'R', 'F') recorded """
    def __init__(self, cmd, nAllowRetry=0):
        self.cmd = cmd
        self.status = 'U' 
        self.retCode = None
        self.nRun = 0
        self.nAllowRetry = nAllowRetry

    def getJob(self):
        if self.status == 'U' and self.nRun <= self.nAllowRetry:
            return self
        else:
            return None
    def setJobRunning(self):
        self.status = 'R'
        self.nRun += 1
    def setJobFinish(self, retCode):
        self.status ='F'
        self.retCode = retCode
    def setJobFailed(self, retCode):
        self.status = 'U'
        self.retCode = retCode
    def dump(self, indent = 0):
        leadingSpace = ''
        if (indent >= deltaIndent):
            leadingSpace = ''.ljust(indent-deltaIndent) + tab

        print leadingSpace,'* cmd = %s'           % self.cmd
        print leadingSpace,'  status = %s'        % self.status
        print leadingSpace,'  retCode = %s'       % self.retCode
        print leadingSpace,'  nRun = %s'          % self.nRun
            
class Scheduler:
    """ Take a JobSet and running maximum poolSize commands at a time """
    def __init__(self, jobset, poolSize=4, debug=False):
        self.jobset = jobset
        self.pool = list()
        self.poolSize = poolSize
        self.debug = debug

    def run(self):
        job = self.jobset.getJob()
        while True:
            if (len(self.pool) < self.poolSize): # we can add new jobs
                if (job != None): # add new jobs
                    self.pool.append(self.issueCommand(job)) # add a new job

            if (len(self.pool) > 0): # there are jobs running
                time.sleep(0.1)
                toDeleteJob = list()
                for i, p in enumerate(self.pool):
                    job, subproc = p[0], p[1]
                    if self.debug: print "i ", i, "job ", job, "subproc ", subproc, "subproc.retcode", subproc.returncode
                    subproc.poll()
                    if subproc.returncode == None: # job is running
                        if (self.debug): print time.ctime(), len(self.pool), "jobs are running"
                        continue
                    else:
                        if subproc.returncode == 0:
                            job.setJobFinish(subproc.returncode)
                        else:
                            job.setJobFailed(subproc.returncode)
                        toDeleteJob.append(i)
                for i in toDeleteJob[::-1]:
                    try:
                        del(self.pool[i])
                    except:
                        print "Delete job exception!"
                        print toDeleteJob
                        self.pool.dump()
                        print len(self.pool)
                        print i
                        raise

            job = self.jobset.getJob()
            if (len(self.pool) == 0 and job == None):
                break

    def issueCommand(self, job):
        job.setJobRunning()
        if self.debug: print time.ctime(), job.cmd, "is issued"
        # os.system(command)
        return (job, subprocess.Popen(job.cmd, shell = True))

##################################################
# Test code for class Job, Jobset and Scheduler
#     a = Job(' ( for i in `seq 2`; do echo $i >> a; done; ) && sleep 2 && rm -f a')
# #     a.getJob().dump() 

#     b1 = Job('echo "b1" >> b1 && sleep 2')
#     b2 = Job('echo "b2" >> b2 && sleep 2')
#     b3 = Job('echo "delete..."&& rm -f b1 b2')

#     jsA = JobSet('jsA')
#     jsA.append(a)

#     jsB = JobSet('jsB')
#     jsB.append(b1)
#     jsB.append(b2)
#     jsB.append(b3)

#     jsC = JobSet('jsC')
#     jsC.append(jsB)

#     jsAll = JobSet('jsAll')
#     jsAll.append(jsA)
#     jsAll.append(jsC)

#     jsAll.dump()

#     s = Scheduler(jsAll)
#     s.run()

#     jsAll.dump()


from string import Template
def trimCompressionSuffix(fileName):
    """
    Trim .gz, .bz2, .tar.gz and .tar.bz2
    """
    try:
        if fileName[-3:] == ".gz":
            fileName = fileName[:-3]
        if fileName[-4:] == ".bz2":
            fileName = fileName[:-4]
        if fileName[-4:] == ".tar":
            fileName = fileName[:-4]
    except IndexError:
        pass
    return fileName


def TemplateCommand(command, inputFileList, fromSuffix, toSuffix, handleCompression = True):
    """
    Use $basename, $fromSuffix and $toSuffix in variable command and construct a list of commands
    e.g.
    ret = TemplateCommand('echo $basename', ["a", "b.gz", "c.tar.gz", "d.bz2", "e.tar.bz2"],
                         fromSuffix = "",
                         toSuffix = "ToSuffix",
                         handleCompression = True)
    print '\n'.join(ret)

    ret = TemplateCommand('echo $basename.$fromSuffix > $basename.$toSuffix', ['a.sam', '/dir/b.sam'], 'sam', 'bam')
    print '\n'.join(ret)

    """
    template = Template(command)
    ret = []
    for i in inputFileList:
        if handleCompression : 
            i = trimCompressionSuffix(i)
            ret.append(template.substitute(basename = i, fromSuffix = fromSuffix, toSuffix = toSuffix ) )
    return ret

# from http://ua.pycon.org/static/talks/kachayev/index.html#/16
def timer(fn):
    def inner(*args, **kwargs):
	t = time()
	fn(*args, **kwargs)
	print "took {time}".format(time=time()-t)
    return inner
# # use like this:
# @timer
# def speak(topic):
#     print "My speach is " + topic
# speak("FP with Python")
