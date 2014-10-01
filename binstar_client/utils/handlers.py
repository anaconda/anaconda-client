import logging
import traceback
import json
import os
import socket

class JSONFormatter(object):

    def __init__(self, *args, **extra_tags):
        self.dumps = extra_tags.pop('dumps', lambda obj: json.dumps(obj, default=lambda obj: str(obj)))

        object.__init__(self, *args)
        self.extra_tags = extra_tags

    def format(self, record):

        if isinstance(record.msg, dict):
            data = record.msg
        elif isinstance(record.msg, (list, tuple)):
            data = {'items': record.msg}
        else:
            data = {'msg':record.msg}

        kwargs = self.extra_tags.copy()

        data.update(logLevel=record.levelname,
                    logModule=record.module,
                    logName=record.name,
                    pid=os.getpid(),
                    **kwargs)

        if record.exc_info:
            etype, value, tb = record.exc_info
            tb = '\n'.join(traceback.format_exception(etype, value, tb))
            data['exception'] = True
            data['traceback'] = tb

        msg = self.dumps(data)
        return msg

class JSONSysLogFormatter(JSONFormatter):
    def __init__(self, appName, *args, **extra_tags):
        self.appName = appName
        JSONFormatter.__init__(self, *args, **extra_tags)

    def format(self, record):
        msg = JSONFormatter.format(self, record)
        return '%s %s' % (self.appName, msg)


def syslog_handler(app_name='binstar-client'):

    address = None
    if os.path.exists('/dev/log'):
        address = '/dev/log'
    elif os.path.exists('/var/run/syslog'):
        address = '/var/run/syslog'
    else:
        address = ('localhost', 514)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(address)
        except:
            return logging.NullHandler()

    hdlr = logging.handlers.SysLogHandler(address=address)
    hdlr.setLevel(logging.INFO)
    hdlr.setFormatter(JSONSysLogFormatter(app_name))
    return hdlr
