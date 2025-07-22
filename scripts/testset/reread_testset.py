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


def read_write_csv(filename_in, filename_out):
    """
    Illustrates correctly reading and writing the test set using Python's csv.
    The output file should be identical to the input file.
    """

    # Read in test set:
    data = list()
    headers = list()
    with open(filename_in, newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile, delimiter="\t",
                                quoting=csv.QUOTE_NONE, quotechar=None)
        headers = reader.fieldnames
        num_fields = len(headers)
        for i, row in enumerate(reader):
            if len(row) != num_fields:
                raise ValueError(f"Row {i}: field count mismatch: expected {num_fields} but got {len(row)}")
            data.append(row)

    # Write out test set:
    with open(filename_out, "w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, headers,
                                delimiter="\t", lineterminator="\n",
                                quoting=csv.QUOTE_NONE, quotechar=None)
        writer.writeheader()
        for row in data:
            writer.writerow(row)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tsv_in", type=str,
                        help="Location of input TSV test set")
    parser.add_argument("pandas_out", type=str,
                        help="Location to output re-written TSV using Pandas")
    parser.add_argument("csv_out", type=str,
                        help="Location to output re-written TSV using csv")
    args = parser.parse_args()

    read_write_pandas(args.tsv_in, args.pandas_out)
    read_write_csv(args.tsv_in, args.csv_out)

    
if __name__ == "__main__":
    main()
