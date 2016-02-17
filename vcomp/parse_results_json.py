
import json
import injectvar
import sys
from collections import defaultdict

VARIANT = "variant"
BAMSTATS = "bamstats"
RESULTS = "results"


class Tabelize(object):
    """
    Writes tab-delimited results in table form to sys.stdout
    """

    def perform_op(self, results):
        var = results[VARIANT]
        for caller,caller_results in results[RESULTS].iteritems():
            for normalizer, norm_results in caller_results.iteritems():
                for comparator, comp_results in norm_results.iteritems():
                    print "\t".join([var, caller, normalizer, comparator, comp_results])

    def finalize(self):
        pass


class NormBreakFinder(object):
    """
    Finds results in which use of VT or V.A.P / leftalign caused vgraph to mismatch, but 'nonorm' was match
    """

    def __init__(self):
        self.breaks = {}
        self.comp_method = "vgraph"
        self.norm_method1 = "vapleft"
        self.nonorm_method = "nonorm"

    def perform_op(self, results):
        for caller in results[RESULTS]:
            try:
                 if results[RESULTS][caller][self.nonorm_method][self.comp_method] == injectvar.MATCH_RESULT and results[RESULTS][caller][self.norm_method1][self.omp_method] != injectvar.MATCH_RESULT:
                     self.breaks[results[VARIANT] + "-" + caller] = self.norm_method1 + ": " + results[RESULTS][caller][self.norm_method1][self.comp_method] + "  " + self.nonorm_method + ": " + results[RESULTS][caller][self.nonorm_method][self.comp_method]
            except:
                pass

    def finalize(self):
        print "Normalization (" + self.norm_method1 + ") causing comparator (" + self.comp_method + ") mismatches:"
        if len(self.breaks)==0:
            print "\tNo normalizer breaking issues detected"
        else:
             for var, result in self.breaks:
                 print var + "\t" + result


class VAPFailsVgraphHits(object):

    def __init__(self):
        self.hits = {}
        self.vgraph = "vgraph"
        self.vapleft = "vapleft"
        self.nonorm = "nonorm"
        self.rawcomp = "raw"

    def perform_op(self, results):
        var_results = results[RESULTS]
        for caller in var_results:
            try:
                vap_result = var_results[caller][self.vapleft][self.rawcomp]
                graph_result = var_results[caller][self.nonorm][self.vgraph]
                if vap_result != graph_result:
                    self.hits[results[VARIANT]] = caller + " " + self.vapleft + ": " + vap_result + "  " + self.vgraph + ": " + graph_result
            except KeyError:
                pass

    def finalize(self):
        print "VAP / raw match fails, matched by " + self.vgraph
        if len(self.hits)==0:
            print "\tNone detected"
        else:
             for var, result in self.hits.iteritems():
                 print var + "\t" + result

class CallerSummary(object):

    def __init__(self):
        self.summary = {}
        self.comparator = "vgraph"
        self.normalizer = "nonorm"


    def perform_op(self, results):
        var_results = results[RESULTS]
        for caller in var_results:
            if caller not in self.summary:
                self.summary[caller] = defaultdict(int)
            cresult = var_results[caller][self.normalizer][self.comparator]
            self.summary[caller][cresult] += 1

    def finalize(self):
        print "Caller summary:"
        print "caller\t" + "\t".join(injectvar.all_result_types)
        for caller in self.summary:
            tot = 0
            for result in self.summary[caller]:
                tot += self.summary[caller][result]
            print caller,
            for res in injectvar.all_result_types:
                print "\t{:.5}".format(100.0*float(self.summary[caller][res])/float(tot)),
            print ""

class GraphCompMismatches(object):

    def __init__(self):
        self.mismatches = {}
        self.comp1 = "vgraph"
        self.comp2 = "happy"
        self.comp3 = "vcfeval"

    def perform_op(self, results):
        var_results = results[RESULTS]
        for caller in var_results:
            for norm_method in var_results[caller]:
                res1 = var_results[caller][norm_method][self.comp1]
                res2 = var_results[caller][norm_method][self.comp2]
                res3 = var_results[caller][norm_method][self.comp3]

                if res1 != res2 or res2 != res3:
                    self.mismatches[results[VARIANT]] = caller + "/ " + norm_method + ": " + self.comp1 + ":" +res1 + "\t" + self.comp2 + ": " +res2 + "\t" + self.comp3 + ": " + res3

    def finalize(self):
        print "Graph comparator mismatches:"
        if len(self.mismatches)==0:
            print "\tNone detected"
        else:
            for k,v in self.mismatches.iteritems():
                print k + "\t" + v


def parseline(line):
    """
    Convert the line of input into a results dict
    :param line:
    :return:
    """
    return json.loads(line)

def main(path, operations=[]):
    line_num = 0
    with open(path) as fh:
        for line in fh.readlines():
            line_num += 1
            if len(line)==0 or line[0] == '#':
                continue
            try:
                results = parseline(line)
            except Exception as ex:
                sys.stderr.write("Error parsing line #" + str(line_num) + ": " + str(ex))
                continue

            for op in operations:
                op.perform_op(results)


    for op in operations:
        print "\n"
        op.finalize()


if __name__=="__main__":
    if len(sys.argv)<2:
        print "Please enter the name of the results file to parse"
        exit(1)

    ops = [
     #   Tabelize(),
        NormBreakFinder(),
    #    VAPFailsVgraphHits(),
        CallerSummary(),
        GraphCompMismatches()
    ]
    main(sys.argv[1], ops)