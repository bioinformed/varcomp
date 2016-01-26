
import subprocess
import gzip
import time
import random
import string
from collections import namedtuple

HOM_REF_GT = "Hom ref."
HET_GT = "Het"
HOM_ALT_GT = "Hom alt."

hom_ref_gts = ["0/0", "0|0"]
het_gts = ["0/1", "1/0", "1|0", "0|1"]
hom_alt_gts = ["1/1", "1|1"]

DEFAULT_CONTIG_ORDER=['1', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '2', '20', '21', '22', '3', '4', '5', '6', '7', '8','9', 'MT', 'X','Y']

def contig_sort_key(var):
    return DEFAULT_CONTIG_ORDER.index(var[0])

def sort_vcf(vcf, conf):

    tmpfile = vcf.replace(".vcf", ".sort.vcf").replace(".gz", "")
    vars = []
    ofh = open(tmpfile, "w")
    if vcf.endswith(".gz"):
        fh = gzip.open(vcf)
    else:
        fh = open(vcf)

    for line in fh.readlines():
         if len(line)>0 and line[0]=='#':
             ofh.write(line)
         else:
             vars.append(line.split('\t'))
    for var in sorted(vars, key=contig_sort_key):
        ofh.write('\t'.join(var))

    ofh.close()
    fh.close()
    return bgz_tabix(tmpfile, conf)

def randstr(length=8):
    return "".join([random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(length)])

def bgz_tabix(path, conf):
    """
    If the path does not end in .gz bgzip the file, then index with tabix and return the potentially modified filename
    :return: Filename of compressed file
    """

    if not path.endswith(".gz"):
        cmd = conf.get('main', 'bgzip_path') + " " + path
        subprocess.check_call(cmd.split())
        path = path + ".gz"
    cmd = conf.get('main', 'tabix_path') + " -f " + path
    subprocess.check_call(cmd.split())

    return path



def set_genotypes(orig_vcf, newGT, region, conf):
    """
    Create a new VCF file that is identical to the given VCF, except that all GT info fields are set to 'newGT'
    """
    fh = None
    if orig_vcf.endswith(".gz"):
        fh = gzip.open(orig_vcf, "r")
    else:
        fh = open(orig_vcf, "r")

    newvcf = orig_vcf.replace(".vcf", ".gtmod" + str(time.time())[-6:].replace(".", "") + ".vcf").replace(".gz", "")
    ofh =open(newvcf, "w")
    for line in fh.readlines():
        if len(line)==0 or line[0]=='#':
            ofh.write(line)
        else:
            toks = line.split('\t')
            chr = toks[0]
            start = int(toks[1])

            if region is not None and (chr != region.chr or start<region.start or start>=region.end):
                ofh.write(line)
                continue

            if len(toks)<10:
                ofh.write(line)
            else:
                if "," in toks[4]:
                    raise ValueError('Cant set GT for multi-alt variants.')
                infoitems = [newGT]
                if ':' in toks[9]:
                    infoitems.extend(toks[9].strip().split(':')[1:] )
                newinfo = ":".join(infoitems)
                ofh.write('\t'.join(toks[0:9] + [newinfo]) + "\n")
    fh.close()
    ofh.close()
    bgz_vcf = bgz_tabix(newvcf, conf)
    return bgz_vcf

def region_to_bedfile(region):
    """
    Write the given region to its own one-line bed file, return the filename
    :param region:
    :return:
    """
    filename = "tmpbed-" + randstr() + ".bed"
    with open(filename, "w") as fh:
        fh.write("\t".join([region.chr, str(region.start), str(region.end)]) + "\n")
    return filename

def vars_to_bed(variants, window=500):
    """
    Generate a bed file containing regions that span each variant, each region is centered
    on the variant start position and extends 'window' bp in each direction
    The resulting file is NOT sorted by
    :param variants: List of variants to create a bed file for
    :param window:Number of bases to extend (from variant start position) in each direction
    :return: Name of bed file created
    """
    bedfilename = "var_regions" + randstr() + ".bed"
    with open(bedfilename, "w") as bfh:
        for var in variants:
            bfh.write("\t".join([var.chrom, str(var.start-window), str(var.start+window)]) + "\n")

    return bedfilename

def read_regions(bedfile):
    """
    Generator for iterating over
    :param bedfile:
    :return:
    """
    Region = namedtuple('Region', ['chr', 'start', 'end'])
    for line in open(bedfile).readlines():
        if len(line)==0 or line[0]=='#':
            continue
        toks = line.split('\t')
        yield Region(toks[0], int(toks[1]), int(toks[2]))

def find_matching_var(vars, region):
    """
    Collect a list of the variants in the vars list whose start position is contained in the given region
    :param vars:
    :param region:
    :param gt:
    :param conf:
    :return:
    """
    matches = [var for var in vars if var.chrom==region.chr and var.start >= region.start and var.start <= region.end]
    return matches


def write_vcf(variants, filename, conf, gt="1/1"):
    """
    Write the variants in the list to a vcf file. Doesn't do any sorting. By default genotype fields are hom alt (1/1)
    :param variants: List of input variants to write
    :param filename: Destination filename of vcf to write
    :param conf: Configuration (needed for paths to tabix, bgzip)
    :param gt: Genotype field
    :return:
    """
    fh = open(filename, "w")
    fh.write("##fileformat=VCFv4.1\n")
    fh.write('##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n')
    fh.write('#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tsample\n')
    for variant in variants:
        fh.write(variant.chrom + "\t")
        fh.write(str(variant.start+1) + "\t") #Remember - internally 0-based coords, but in vcf 1-based
        fh.write("." + "\t")
        fh.write(variant.ref + "\t")
        fh.write(variant.alts[0] + "\t")
        fh.write("100" + "\t")
        fh.write("PASS" + "\t")
        fh.write("." + "\t")
        fh.write("GT" + "\t")
        fh.write(gt + "\n")
    fh.close()
    return compress_vcf(filename, conf)


def compress_vcf(input_vcf, conf):
    """
    If the input vcf's filename does not end with .gz, compress and index it with bgzip / tabix
    :param input_vcf:
    :param conf:
    :return: Name of compressed vcf file, typically input_vcf + '.gz'
    """
    if not input_vcf.endswith(".gz"):
        cmd = conf.get('main', 'bgzip_path') + " -f " + input_vcf
        subprocess.check_call(cmd, shell=True)
        cmd = conf.get('main', 'tabix_path') + " -f " + input_vcf + ".gz"
        subprocess.check_call(cmd, shell=True)
        input_vcf = input_vcf + '.gz'
    return input_vcf


def get_first_gt(var):
    """
    Returns string version of GT field.. Hack until we can get pysam to work..
    :param var:
    """
    toks = str(var).split()
    if len(toks) <= 9:
        return None

    gt = toks[9].split(":")[0]
    if gt in hom_ref_gts:
        return HOM_REF_GT
    if gt in hom_alt_gts:
        return HOM_ALT_GT
    if gt in het_gts:
        return HET_GT
    return gt