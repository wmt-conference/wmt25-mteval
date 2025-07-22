#!/usr/bin/env python3

import argparse
import collections
import csv
import pandas


def read_write_pandas(filename_in, filename_out):
    """
    Illustrates correctly reading and writing the test set using Pandas.
    The output file should be identical to the input file.
    """
    df = pandas.read_csv(filename_in,
                         sep="\t",
                         quoting=csv.QUOTE_NONE,
                         header=0,
                         dtype=collections.defaultdict(pandas.StringDtype, segment_id="Int64"),
                         keep_default_na=False)
    df.to_csv(filename_out, sep="\t", quoting=csv.QUOTE_NONE, index=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tsv_in", type=str,
                        help="Location of input TSV test set")
    parser.add_argument("pandas_out", type=str,
                        help="Location to output re-written TSV using Pandas")
    args = parser.parse_args()

    read_write_pandas(args.tsv_in, args.pandas_out)

    
if __name__ == "__main__":
    main()
