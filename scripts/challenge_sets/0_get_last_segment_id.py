''' I wrote this script to parse the general TSV file and get the highest segment_id per langpair, but it is not needed
any more. ~~~Lefteris'''

import argparse
import csv
from collections import defaultdict



def get_last_segment_ids(tsv_filename):
    with open(tsv_filename) as tsv_file:
        reader = csv.DictReader(tsv_file, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        segment_id_per_langpair = defaultdict(int)
        i = 0
        for row in reader:
            i +=1
            langpair = f"{row['source_lang']}-{row['target_lang']}"
            langpair = langpair.split("_")[0]
            try:
                segment_id = int(row['segment_id'])
            except TypeError:
                continue
            except ValueError as e:
                print(i, row)
                continue
            if segment_id > segment_id_per_langpair[langpair]:
                segment_id_per_langpair[langpair] = segment_id

        for langpair, last_segment_id in segment_id_per_langpair.items():
            print(f"{langpair}: {last_segment_id}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--tsv_file', required=True, type=str,
                      help="The target TSV file that will be read")
    args = parser.parse_args()
    tsv_filename = args.tsv_file
    get_last_segment_ids(tsv_filename)


