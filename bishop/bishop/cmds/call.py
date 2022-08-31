import time
import random
from functools import partial
from pprint import pprint

from .. rep.assembly import GenomeAssemblyMetadata
from .. rep.vcf import VCF
from .. rep.region import Region
from .. ann.flank import VariantFlanks
from .. ann.iters import *
from .. ann.fingerprint import ComparisonTask
from .. io.intervals import load_interval_lists
from .. ann.classify import Classifier, AnnotateCozy, ClassifyTask

from pysam import VariantFile

import sys
import argparse

parser = argparse.ArgumentParser(description='Train allele specific classification')
parser.add_argument(
    '--query_vcf',
    dest='query_vcf_path',
    required=True,
    help='Path to VCF to call'
)
parser.add_argument(
    '--classifier',
    dest='classifier_path',
    default='classifier.pickle',
    help='Path to pickled classifier'
)
parser.add_argument(
    '--assembly',
    dest='assembly_name',
    default='GRCh38.p14',
    help='Name of the geome assembly to use'
)
parser.add_argument(
    '--output',
    dest='output_vcf_path',
    default='called.vcf',
    help='Path to generated VCF',
)
# XXX: add support for interval lists
# XXX: do entire genome if not provided
parser.add_argument(
    '-R', '--region',
    required=True,
    type=str,
    help='Region to generate results from'
)

#parser.add_argument('--skip_filtered', action='store_true', default=False, help='While building training set, skip filtered sites')

parser.add_argument(
    '-S', '--stratification',
    dest='strat_intervals',
    action='append', 
    type=str,
    help='Interval file for labeling lookup'
)


def call(
    query_vcf_path=None, 
    output_vcf_path=None, 
    classifier_path=None,
    assembly_name=None,
    strat_intervals=None,
    region=None,
    as_scheme='ucsc'
):
    ga = GenomeAssemblyMetadata.load(assembly_name)
    overlaps = load_interval_lists(strat_intervals, astype='dataframe')
    query_vcf = VCF(query_vcf_path, metadata=ga, ignore_missing=True)
    specs = [
        {'ID': 'BLOD', 'Description': 'Bishop LOD', 'Type': 'Float', 'Number': 1},
        {'ID': 'AS_BLOD', 'Description': 'Allele Specific Bishop LOD', 'Type': 'Float', 'Number': 'A'},
    ]
    for spec in specs:
        items = list(spec.items())
        query_vcf.header.add_meta(key='INFO', items=items)
    output_vcf = query_vcf.to_writer(output_vcf_path)
    annotate_func = AnnotateCozy()
    classifier = Classifier.load_classifier(classifier_path)
    # XXX: support pandas dataframe saving as well?
    cls = ClassifyTask(
        query_vcf=query_vcf,
        classifier=classifier,
        overlaps=overlaps,
        annotate=annotate_func,
        assembly=ga,
        as_scheme=as_scheme,
    )
    cls.call_vcf_sites(output_vcf=output_vcf, region=region)

def main(args):
    call(
        query_vcf_path=args.query_vcf_path,
        output_vcf_path=args.output_vcf_path,
        classifier_path=args.classifier_path,
        assembly_name=args.assembly_name,
        strat_intervals=args.strat_intervals,
        region=args.region,
    )

def validate_args(args):
    pass

def main_cli():
    intn = lambda it: it.split('=') if '=' in it else (it.split('/')[-1], it)
    hdr = ('name', 'path')
    args = parser.parse_args()
    args.strat_intervals = [dict(zip(hdr, intn(it))) for it in args.strat_intervals]
    args.region = Region(args.region)
    validate_args(args)
    main(args)

if __name__ == "__main__":
    main_cli()
