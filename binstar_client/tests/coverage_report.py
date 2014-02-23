'''
Created on Sep 23, 2013

@author: sean
'''
from coverage.summary import SummaryReporter
from coverage.results import Numbers
from coverage.misc import NotPython
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
    return FAIL + text + ENDC

def orange(text):
    return WARNING + text + ENDC

def blue(text):
    return OKBLUE + text + ENDC

class ColorSummaryReporter(SummaryReporter):
    
    @property    
    def fmt_name(self):
        max_name = max([len(cu.name) for cu in self.code_units] + [5])
        fmt_name = "%%- %ds  " % max_name
        return fmt_name

    def fmt_coverage(self, perc):
        
        fmt_coverage = self.fmt_name + "%6d %6d"
        if self.branches:
            fmt_coverage += " %6d %6d"
        width100 = Numbers.pc_str_width()
        color = green
        if perc < 80:
            color = blue
        if perc < 50:
            color = red
        
        fmt_coverage += color("%%%ds%%%%" % (width100+3,))
        if self.config.show_missing:
            fmt_coverage += "   %s"
        fmt_coverage += "\n"
        return fmt_coverage

    def header(self):
        header = (self.fmt_name % "Name") + " Stmts   Miss"
        if self.branches:
            header += " Branch BrMiss"
        width100 = Numbers.pc_str_width()
        header += "%*s" % (width100+4, "Cover")
        header += "\n"
        return header
    
    def report(self, morfs, outfile=None):
        """Writes a report summarizing coverage statistics per module.

        `outfile` is a file object to write the summary to.

        """
        self.find_code_units(morfs)

        # Prepare the formatting strings
        
        fmt_err = "%s   %s: %s\n"
        
        header = self.header()
#         fmt_coverage = self.fmt_coverage()
        rule = "-" * len(header) + "\n"

        if not outfile:
            outfile = sys.stdout

        # Write the header
        outfile.write(header)
        outfile.write(rule)

        total = Numbers()

        for cu in self.code_units:
            try:
                analysis = self.coverage._analyze(cu)
                nums = analysis.numbers
                args = (cu.name, nums.n_statements, nums.n_missing)
                if self.branches:
                    args += (nums.n_branches, nums.n_missing_branches)
                args += (nums.pc_covered_str,)
                if self.config.show_missing:
                    args += (analysis.missing_formatted(),)
                outfile.write(self.fmt_coverage(nums.pc_covered) % args)
                total += nums
            except KeyboardInterrupt:                   # pragma: not covered
                raise
            except:
                report_it = not self.config.ignore_errors
                if report_it:
                    typ, msg = sys.exc_info()[:2]
                    if typ is NotPython and not cu.should_be_python():
                        report_it = False
                if report_it:
                    outfile.write(fmt_err % (cu.name, typ.__name__, msg))

        if total.n_files > 1:
            outfile.write(rule)
            args = ("TOTAL", total.n_statements, total.n_missing)
            if self.branches:
                args += (total.n_branches, total.n_missing_branches)
            args += (total.pc_covered_str,)
            if self.config.show_missing:
                args += ("",)
#             outfile.write(self.fmt_coverage(total.pc_covered) % args)
        return total


def report(cov, morfs=None, show_missing=False, ignore_errors=None,
                file=None,                          # pylint: disable=W0622
                omit=None, include=None
                ):
        cov._harvest_data()
        cov.config.from_args(
            ignore_errors=ignore_errors, omit=omit, include=include,
            show_missing=show_missing,
            )
        reporter = ColorSummaryReporter(cov, cov.config)
        return reporter.report(morfs, outfile=file)
