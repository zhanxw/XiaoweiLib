import sys
class Task:
    taskId = 0
    def __init__(self, cmd, name = None):
        self.name = name
        self.cmd = cmd
        self.taskId = Task.taskId
        Task.taskId += 1

    def __str__(self):
        if self.name:
            return self.getId() + "[ " + self.name+":"+self.cmd + " ]"
        else:
            return self.getId() + "[ Unknown ]"
    def __repr__(self):
        return self.__str__()

    def printNode(self, indent):
        print " " * indent + repr(self)

    def getId(self):
        return 'Task-%d' % self.taskId

    def generateDep(self):
        # key: id ;  val: [ depTarget, commands]
        return {self.getId() : [ [], [self.cmd] ] }
    
    def lastTask(self):
        return self.getId()

class SerialTask(list):
    taskId = 0;
    def __init__(self):
        self.taskId = SerialTask.taskId
        SerialTask.taskId += 1
    def printNode(self, indent):
        print ' ' * indent + self.getId()
        for n in self:
            if isinstance(n, Task):
                n.printNode(indent + 4)
            elif isinstance(n, SerialTask) or isinstance(n, ParallelTask):
                n.printNode(indent + 4)
            else:
                print >> sys.stderr, "unknwon type"
    def getId(self):
        return 'Serial-%d' % self.taskId
    def generateDep(self):
        ret = {}
        for idx, i in enumerate(self):
            if idx > 0:
            #     ret[ self[idx].getId() ] = [ [ self.getId()], []]
            # else:
                ret[ self[idx].getId() ] = [ [ self[idx-1].getId() ], []]
        if len(self) ==  0:
            ret[self.getId()] = [ [], []]
        else:
            ret[self.getId()] = [ [self[-1].getId()], []]

        for i in self:
            r = i.generateDep()
            for k, v in r.iteritems():
                if k in ret:
                    ret[k][0].extend(v[0])
                    ret[k][1].extend(v[1])
                else:
                    ret[k] = v
        return ret
    def lastTask(self):
        if len(self) == 0:
            return self.getId()
        return self[-1].lastTask()

class ParallelTask(list):
    taskId = 0
    def __init__(self):
        self.taskId = ParallelTask.taskId
        ParallelTask.taskId += 1
    def printNode(self, indent):
        print ' ' * indent + self.getId()
        for n in self:
            if isinstance(n, Task):
                n.printNode(indent + 4)
            elif isinstance(n, SerialTask) or isinstance(n, ParallelTask):
                n.printNode(indent + 4)
            else:
                print >> sys.stderr, "unknwon type"
    def getId(self):
        return 'Parallel-%d' % self.taskId

    def generateDep(self):
        ret = {}
        deps = [i.getId() for i in self]
        ret[self.getId()] = [ deps, []]
        for i in self:
            r = i.generateDep()
            for k, v in r.iteritems():
                if k in ret:
                    ret[k][0].extend(v[0])
                    ret[k][1].extend(v[1])
                else:
                    ret[k] = v
        return ret
    def lastTask(self):
        return self.getId()

class TaskTree:
    def __init__(self):
        self.task = SerialTask()
        self.current = self.task
        self.parent = []
        self.totalTask = 0

    def beginSerial(self):
        self.parent.append(self.current)
        new = SerialTask()
        self.current.append(new)
        self.current = new

    def endSerial(self):
        self.current = self.parent.pop()
        
    def beginParallel(self):
        self.parent.append(self.current)
        new = ParallelTask()
        self.current.append(new)
        self.current = new

    def endParallel(self):
        self.current = self.parent.pop()
        
    def addTask(self, cmd, name = None):
        self.totalTask += 1
        if name:
            self.current.append(Task(cmd = cmd, name = name))
        else:
            self.current.append(Task(cmd = cmd, name = "Task%d" % self.totalTask))

    def sanityCheck(self):
        if len(self.parent) != 0: 
            print >> sys.stderr, "Unblanced task groups, results may be unreliable"
            
    def dump(self):
        self.sanityCheck()

        ##print type(self.task)
        print (self.task)
        ##print "Total", self.totalTask, "task(s)."

    def dumpTree(self):
        self.task.printNode(0)
        ##print "Total", self.totalTask, "task(s)."

    def generateDep(self):
        ## print "Total", self.totalTask, "task(s)."
        return self.task.generateDep()
    #' @param out which file to write to
    #' @param donePrefix if true, then generate .done file
    #' @param timeDelay, use 'sleep [randomSeconds]' to let jobs submitted at random time points.
    def printDep(self, out = sys.stdout, donePrefix = None, timeDelay = None):
        from random import randint
        from os.path import abspath
        nodepIds = []
        targets = set()
        deps = set()
        print >> out , ".DELETE_ON_ERROR:"
        print >> out , "all: _all"
        for k, v in self.generateDep().iteritems():
            if donePrefix:
                k =  "%s/%s.done" % (donePrefix, k)  
                v[0] = [ "%s/%s.done" % (donePrefix, i)  for i in v[0] ]
            print >> out, k, ":",  ' '.join(v[0])
            if timeDelay:
                sleepTime = randint(1, timeDelay)
                print >> out, "\tsleep %d" % sleepTime
            for c in v[1]:
                print >>out,  "\t", c
            if donePrefix:
                print >>out,  "\ttouch %s" % abspath(k)

            if len(v[0]) == 0 and len(v[1]) == 0:
                nodepIds.append(k)
            targets.add(k)
            for i in v[0]:
                deps.add(i)
        print >> out, ".PHONY : ", " ".join(nodepIds)
        print >> out, "_all : ", " ".join(list(targets - deps))

    def __len__(self):
        return self.totalTask
