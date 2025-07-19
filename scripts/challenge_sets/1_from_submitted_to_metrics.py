import argparse
import csv
import glob
import os

FIELDNAMES = [
    'doc_id',
    'segment_id',
    'source_lang',
    'target_lang',
    'set_id',
    'system_id',
    'source_segment',
    'hypothesis_segment',
    'reference_segment',
    'domain_name',
    'method'
]


def traverse_source_dir(input_directory):
    # Process files in the first level of subdirectories

    for challenge_set_name in next(os.walk(input_directory))[1]:
        challenge_set_path = os.path.join(input_directory, challenge_set_name)

        # get the language pairs covered by this challenge set
        langpairs = set([filename.split('.')[1] for filename in os.listdir(challenge_set_path)])

        segment_n = 0

        for langpair in sorted(list(langpairs)):
            if langpair in ["README", "history", "readme"]:
                continue
            source_lang, target_lang = langpair.split('-')

            # resolve the filenames for the langpair
            hypothesis_filenames, meta_filename, reference_filename, source_filename = resolve_filenames(
                challenge_set_name, challenge_set_path, langpair)

            with open(source_filename) as source_file, \
                open(meta_filename) as meta_file:
                meta_reader = csv.reader(meta_file, delimiter='\t')
                next(meta_reader)
                try:
                    reference_file = open(reference_filename)
                    reference_exists = True
                except FileNotFoundError:
                    reference_exists = False
                    reference_file = None
                hypothesis_files = [open(hypothesis_filename) for hypothesis_filename in sorted(hypothesis_filenames)]

                for source_segment in source_file:
                    source_segment = source_segment.strip()
                    segment_n += 1
                    try:
                        row = next(meta_reader)
                        domain_name, doc_id = row
                    except StopIteration:
                        domain_name = 'None'
                        doc_id = f"{challenge_set_name}_unknown"

                    set_id = f"challenge_{challenge_set_name}"
                    method = ""

                    # segment_id = f"challenge_{challenge_set_name}_#_{langpair}_#_{doc_id}_#_{segment_n}"

                    if reference_exists:
                        reference_segment = next(reference_file).strip()
                    else:
                        reference_segment = ""
                    for hypothesis_file in hypothesis_files:
                        hypothesis_segment = next(hypothesis_file).strip()
                        system_id = os.path.basename(hypothesis_file.name).split('.')[2] # as in hyp-1, hyp-2

                        yield {'doc_id': doc_id,
                               'segment_id': segment_n,
                               'source_lang': source_lang,
                               'target_lang': target_lang,
                               'set_id': set_id,
                               'system_id': system_id,
                               'source_segment': source_segment,
                               'hypothesis_segment': hypothesis_segment,
                               'reference_segment': reference_segment,
                               'domain_name': domain_name,
                               'method': method}


def resolve_filenames(challenge_set_name, challenge_set_path, langpair):
    source_filename = os.path.join(challenge_set_path, f"{challenge_set_name}.{langpair}.src.txt")
    reference_filename = os.path.join(challenge_set_path, f"{challenge_set_name}.{langpair}.ref.txt")
    meta_filename = os.path.join(challenge_set_path, f"{challenge_set_name}.{langpair}.meta.txt")
    if not os.path.isfile(meta_filename):
        meta_filename = os.path.join(challenge_set_path, f"{challenge_set_name}.{langpair}.meta.tsv")
    hypothesis_glob = os.path.join(challenge_set_path, f"{challenge_set_name}.{langpair}.hyp-*.txt")
    hypothesis_filenames = glob.glob(hypothesis_glob)
    return hypothesis_filenames, meta_filename, reference_filename, source_filename


def convert_challenge_sets(input_directory, output_tsv_filename):
    with open(output_tsv_filename, 'w') as output_tsv:
        writer = csv.DictWriter(output_tsv, fieldnames=FIELDNAMES, delimiter='\t')
        for row in traverse_source_dir(input_directory):
            writer.writerow(row)



if __name__ == '__main__':
    # Create output subdirectories if they don't exist

    parser = argparse.ArgumentParser()
    parser.add_argument('--input_dir', required=True, type=str,
                      help="The directory where challenge set submissions exist")
    parser.add_argument('--output_tsv', required=True, type=str,
                      help="The target TSV file where inputs will be placed")
    args = parser.parse_args()
    convert_challenge_sets(args.input_dir, args.output_tsv)

