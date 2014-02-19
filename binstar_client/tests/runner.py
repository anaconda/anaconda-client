'''
Created on Sep 23, 2013

@author: sean
'''
from unittest.runner import TextTestRunner, TextTestResult
from unittest.signals import registerResult
import time
import sys

WARNING = '\033[33m'
OKBLUE = '\033[34m'
OKGREEN = '\033[32m'
FAIL = '\033[31m'
ENDC = '\033[0m'
BOLD = "\033[1m"

def green(text):
    return BOLD + OKGREEN + text + ENDC

def red(text):
    return BOLD + FAIL + text + ENDC

def orange(text):
    return WARNING + text + ENDC

def blue(text):
    return OKBLUE + text + ENDC

class ColorTextTestResult(TextTestResult):
    def addSuccess(self, test):
        super(TextTestResult, self).addSuccess(test)
        if self.showAll:
            self.stream.writeln(green("ok"))
        elif self.dots:
            self.stream.write('.')
            self.stream.flush()

    def addError(self, test, err):
        super(TextTestResult, self).addError(test, err)
        if self.showAll:
            self.stream.writeln(red("ERROR"))
        elif self.dots:
            self.stream.write(red('E'))
            self.stream.flush()

    def addFailure(self, test, err):
        super(TextTestResult, self).addFailure(test, err)
        if self.showAll:
            self.stream.writeln(red("FAIL"))
        elif self.dots:
            self.stream.write(red('F'))
            self.stream.flush()

    def addSkip(self, test, reason):
        super(TextTestResult, self).addSkip(test, reason)
        if self.showAll:
            self.stream.writeln(blue("skipped {0!r}".format(reason)))
        elif self.dots:
            self.stream.write(blue("s"))
            self.stream.flush()

    def addExpectedFailure(self, test, err):
        super(TextTestResult, self).addExpectedFailure(test, err)
        if self.showAll:
            self.stream.writeln(blue("expected failure"))
        elif self.dots:
            self.stream.write(blue("x"))
            self.stream.flush()

    def addUnexpectedSuccess(self, test):
        super(TextTestResult, self).addUnexpectedSuccess(test)
        if self.showAll:
            self.stream.writeln(blue("unexpected success"))
        elif self.dots:
            self.stream.write(blue("u"))
            self.stream.flush()

    def printErrors(self):
        if self.dots or self.showAll:
            self.stream.writeln()
        self.printErrorList(red('ERROR'), self.errors)
        self.printErrorList(red('FAIL'), self.failures)

class ColorTextTestRunner(TextTestRunner):

    def __init__(self, stream=sys.stderr, descriptions=True, verbosity=1,
        failfast=False, buffer=False, resultclass=ColorTextTestResult):
        
        TextTestRunner.__init__(self, stream=stream, descriptions=descriptions,
                                verbosity=verbosity, failfast=failfast, buffer=buffer,
                                resultclass=resultclass)
    def run(self, test):
        "Run the given test case or test suite."
        result = self._makeResult()
        registerResult(result)
        result.failfast = self.failfast
        result.buffer = self.buffer
        startTime = time.time()
        startTestRun = getattr(result, 'startTestRun', None)
        if startTestRun is not None:
            startTestRun()
        try:
            test(result)
        finally:
            stopTestRun = getattr(result, 'stopTestRun', None)
            if stopTestRun is not None:
                stopTestRun()
        stopTime = time.time()
        timeTaken = stopTime - startTime
        result.printErrors()
        if hasattr(result, 'separator2'):
            self.stream.writeln(result.separator2)
        run = result.testsRun
        self.stream.writeln("Ran %d test%s in %.3fs" % 
                            (run, run != 1 and "s" or "", timeTaken))
        self.stream.writeln()


        return result
    
    def write_end(self, result, coverage):
        
        expectedFails = unexpectedSuccesses = skipped = 0
        try:
            results = map(len, (result.expectedFailures,
                                result.unexpectedSuccesses,
                                result.skipped))
        except AttributeError:
            pass
        else:
            expectedFails, unexpectedSuccesses, skipped = results
            
        infos = []
        if not result.wasSuccessful():
            self.stream.write('Tests: ' + red("FAILED"))
            failed, errored = map(len, (result.failures, result.errors))
            if failed:
                infos.append("failures=%d" % failed)
            if errored:
                infos.append("errors=%d" % errored)
        else:
            self.stream.write('Tests: ' + green("OK"))
        if skipped:
            infos.append("skipped=%d" % skipped)
        if expectedFails:
            infos.append("expected failures=%d" % expectedFails)
        if unexpectedSuccesses:
            infos.append("unexpected successes=%d" % unexpectedSuccesses)
        if infos:
            self.stream.write(" (%s)" % (", ".join(infos),))
            
        perc = coverage.pc_covered
        color = green
        if perc < 80:
            color = blue
        if perc < 50:
            color = red
        
        cv = color("%i%%" % (int(coverage.pc_covered)))
        self.stream.write(", Coverage: %s \n" % (cv))
        
        
