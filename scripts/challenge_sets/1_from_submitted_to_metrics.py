import argparse
import csv
import glob
import os
import re


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

NEWLINES_REGEX = re.compile("\\s*\n\\s*")


def trim_and_escape(text):
    fixed = text.strip().replace("\t", " ")
    # # there are literal tabs, not sure if we would want to replace them too though
    if "    " in fixed:
        fixed = fixed.replace("    ", " ")
    return NEWLINES_REGEX.sub(r" \\n ", fixed)


def traverse_source_dir(input_directory):
    # Process files in the first level of subdirectories

    for challenge_set_name in next(os.walk(input_directory))[1]:
        challenge_set_path = os.path.join(input_directory, challenge_set_name)

        # get the language pairs covered by this challenge set
        langpairs = set([filename.split('.')[1] for filename in os.listdir(challenge_set_path)])

        for langpair in sorted(list(langpairs)):
            if langpair in ["README", "history", "readme"]:
                continue
            source_lang, target_lang = langpair.split('-')

            # resolve the filenames for the langpair by looking into the directory
            hypothesis_filenames, meta_filename, reference_filename, source_filename = resolve_filenames(
                challenge_set_name, challenge_set_path, langpair)

            # open the source and the meta files
            with open(source_filename) as source_file, open(meta_filename) as meta_file:

                # the metadata file needs to be read as a csv as it has two columns
                meta_reader = csv.reader(meta_file, delimiter='\t', quoting=csv.QUOTE_NONE, quotechar=None)


                # challenge sets may or may not have a reference, so try to look for a reference file, if not, leave the
                # field empty
                try:
                    reference_file = open(reference_filename)
                    reference_exists = True
                except FileNotFoundError:
                    reference_exists = False
                    reference_file = None

                # open the hypothesis filenames / using a loop because their number may be
                # different for every challenge set and/or langpair
                hypothesis_files = [open(hypothesis_filename) for hypothesis_filename in sorted(hypothesis_filenames)]

                segment_id = 0
                stopiteration = False

                # iterate based on the open source file
                for source_segment in source_file:

                    # remove useless trailing spaces and linebreaks
                    source_segment = source_segment.strip()

                    # there is a segment id for each challenge set, that increments for every source
                    segment_id += 1

                    # read the metadata for this source, create dummy metadata if the metadata file ends earlier
                    # (happened with one challenge set)

                    try:
                        row = next(meta_reader)

                        # skip the header if it exists (some challenge sets have it, some not)
                        if 'doc_id' in row:
                            row = next(meta_reader)

                        try:
                            domain_name, doc_id = row
                        except ValueError as e:
                            print(meta_filename, segment_id, row)
                            raise(e)

                        domain_name = domain_name.strip()
                        doc_id = doc_id.strip()
                    except StopIteration:
                        domain_name = 'NaN'
                        doc_id = f"{challenge_set_name}_unknown"
                        stopiteration = True

                    set_id = f"challenge_{challenge_set_name}"
                    method = "NaN"

                    # get the reference text
                    if reference_exists:
                        reference_segment = next(reference_file).strip()
                    else:
                        reference_segment = "NaN"

                    # create a new row for every hypothesis, the nane of the hypothesis will be the system id
                    for hypothesis_file in hypothesis_files:
                        hypothesis_segment = next(hypothesis_file).strip()
                        system_id = os.path.basename(hypothesis_file.name).split('.')[2] # as in hyp-1, hyp-2

                        yield {'doc_id': doc_id,
                               'segment_id': segment_id,
                               'source_lang': source_lang,
                               'target_lang': target_lang,
                               'set_id': set_id,
                               'system_id': system_id,
                               'source_segment': trim_and_escape(source_segment),
                               'hypothesis_segment': trim_and_escape(hypothesis_segment),
                               'reference_segment': trim_and_escape(reference_segment),
                               'domain_name': domain_name,
                               'method': method}

                if stopiteration:
                    print("Warning, the following metadata file was shorter than the sources file:", meta_filename)


def resolve_filenames(challenge_set_name, challenge_set_path, langpair):
    source_filename = os.path.join(challenge_set_path, f"{challenge_set_name}.{langpair}.src.txt")
    reference_filename = os.path.join(challenge_set_path, f"{challenge_set_name}.{langpair}.ref.txt")
    meta_filename = os.path.join(challenge_set_path, f"{challenge_set_name}.{langpair}.meta.txt")
    if not os.path.isfile(meta_filename):
        meta_filename = os.path.join(challenge_set_path, f"{challenge_set_name}.{langpair}.meta.tsv")
    hypothesis_glob = os.path.join(challenge_set_path, f"{challenge_set_name}.{langpair}.hyp*.txt")
    hypothesis_filenames = glob.glob(hypothesis_glob)
    return hypothesis_filenames, meta_filename, reference_filename, source_filename


def convert_challenge_sets(input_directory, output_tsv_filename):
    with open(output_tsv_filename, 'w') as output_tsv:
        writer = csv.DictWriter(output_tsv, fieldnames=FIELDNAMES, delimiter='\t', quoting=csv.QUOTE_NONE,
                                quotechar=None)
        for row in traverse_source_dir(input_directory):
            writer.writerow(row)



if __name__ == '__main__':
    # Create output subdirectories if they don't exist

    parser = argparse.ArgumentParser()
    parser.add_argument('--input_dir', required=True, type=str,
                      help="The directory where challenge set submissions exist")
    parser.add_argument('--output_tsv', required=True, type=str,
                      help="The target TSV file where inputs will be placed")
    parser.add_argument('--config', required=True, type=str, default=None,
                        help="configuration file")
    args = parser.parse_args()

    # if args.config:
    #     with open(args.config) as configfile:
    #         config = yaml.safe_load(configfile)
    #         starting_ids = config['starting_ids']
    # else:
    #     starting_ids = {}

    convert_challenge_sets(args.input_dir, args.output_tsv)

