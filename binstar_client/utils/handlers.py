
import sys
import logging

class MyStreamHandler(logging.Handler):
    WARNING = '\033[93m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = "\033[1m"
    COLOR_MAP = {'ERROR': '%s%s[%%s]%s' % (BOLD, FAIL, ENDC),
                 'WARNING': '%s%s[%%s]%s' % (BOLD, WARNING, ENDC),
                 'DEBUG': '%s%s[%%s]%s' % (BOLD, OKBLUE, ENDC),
                 }
    
    def color_map(self, header, level):
        return self.COLOR_MAP.get(level,'[%s]') % header  
    
    def emit(self, record):
        if record.levelno == logging.INFO:
            header = None
            message = record.getMessage()
            stream = sys.stdout
        else:
            stream = sys.stderr
            if record.exc_info:
                err = record.exc_info[1]
                header = type(err).__name__
                if err.args:
                    message = err.args[0]
                else:
                    message = str(err)
            else:
                header = record.levelname.lower()
                message = record.getMessage()
        
        if header:
            if stream.isatty() and not sys.platform.startswith('win'):
                header = self.color_map(header, record.levelname)
            stream.write('%s %s\n' % (header, message))
        else:
            stream.write('%s\n' % message)

