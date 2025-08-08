
import os
import csv
import argparse
from typing import Dict, List
from tqdm import tqdm


class SubmissionProcessor:
    """
    A class to process submission details and segment files.

    @ivar input_directory: Path to the input directory containing segment files.
    @ivar output_directory: Path to the output directory to save filtered TSV files.
    @ivar submission_details_tsv: Path to the TSV file containing submission details.
    """

    def __init__(self, input_directory: str, output_directory: str, submission_details_tsv: str):
        self.input_directory = input_directory
        self.output_directory = output_directory
        self.submission_details_tsv = submission_details_tsv
        self.submission_map = self._read_submission_details()

    def _read_submission_details(self) -> Dict[str, str]:
        """
        Reads the submission details TSV file and returns a dictionary mapping submission_id to system_name.

        @return: Mapping from submission ID to system name.
        """
        submission_map = {}
        with open(self.submission_details_tsv, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file, delimiter='\t', quoting=csv.QUOTE_NONE, quotechar=None)
            if 'ID' not in reader.fieldnames or 'System Name' not in reader.fieldnames:
                # display the filename that has the issue
                print(f"Error: The submission details TSV file '{self.submission_details_tsv}' is missing required columns.")
                raise ValueError("The submission details TSV file must contain 'ID' and 'System Name' columns.")
            # Read each row and populate the submission_map
            for row in reader:
                submission_id = row['ID']
                system_name = row['System Name']
                submission_map[submission_id] = system_name
        return submission_map

    def _find_segment_files(self) -> List[str]:
        """
        Traverses the input directory to find all segments.tsv files.

        @return: List of paths to segments.tsv files.
        """
        segment_files = []
        for root, _, files in os.walk(self.input_directory):
            for file in files:
                if file == 'segments.tsv':
                    segment_files.append(os.path.join(root, file))
        return segment_files

    def _process_segment_file(self, file_path: str):
        """
        Processes a single segments.tsv file and writes filtered rows to the output directory.

        @param file_path: Path to the segments.tsv file.
        """
        path_parts = file_path.split(os.sep)
        slot = path_parts[-3]
        submission_id = path_parts[-2]
        system_name = self.submission_map.get(submission_id, submission_id)

        with open(file_path, mode='r', newline='', encoding='utf-8') as infile:
            reader = csv.DictReader(infile, delimiter='\t', quoting=csv.QUOTE_NONE, quotechar=None)
            rows = [row for row in reader if row['set_id'].startswith('challenge_')]

        challenge_sets = {}
        for row in rows:
            challenge_set_name = row['set_id'].replace('challenge_', '', 1)
            if challenge_set_name not in challenge_sets:
                challenge_sets[challenge_set_name] = []
            challenge_sets[challenge_set_name].append(row)

        for challenge_set_name, challenge_rows in challenge_sets.items():
            output_dir = os.path.join(self.output_directory, challenge_set_name, slot)
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"{system_name}.tsv")

            with open(output_file, mode='w', newline='', encoding='utf-8') as outfile:
                writer = csv.DictWriter(outfile, fieldnames=challenge_rows[0].keys(), delimiter='\t',
                                        quoting=csv.QUOTE_NONE, quotechar=None)
                writer.writeheader()
                writer.writerows(challenge_rows)


    def process_all(self):
        """
        Processes all segment files found in the input directory.
        """

        segment_files = self._find_segment_files()
        if not segment_files:
            print(f"No segment files found in the directory: {self.input_directory}")
            return
        print(f"Found {len(segment_files)} segment files to process.")
        # Process each segment file
        print("Processing segment files...")
        if not os.path.exists(self.output_directory):
            os.makedirs(self.output_directory, exist_ok=True)
        else:
            print(f"Output directory '{self.output_directory}' already exists. Files will be overwritten.")
        print("Starting to process each segment file...")
        print(f"Output will be saved in: {self.output_directory}")
        for file_path in tqdm(segment_files, desc="Processing segment files", unit="file"):
            self._process_segment_file(file_path)

        self.generate_summary_table(os.path.join(self.output_directory,'summary.tsv'))

        print("All segment files processed successfully.")

    def generate_summary_table(self, summary_output_path: str):
        """
        Generates a TSV summary table showing the number of segments per system for each challenge set.

        @param summary_output_path: Path to save the summary TSV file.
        """
        from collections import defaultdict

        # Dictionary: challenge_set_name -> system_name -> count
        summary_data = defaultdict(lambda: defaultdict(int))
        system_names = set()

        for challenge_set_name in os.listdir(self.output_directory):
            challenge_set_path = os.path.join(self.output_directory, challenge_set_name)
            if not os.path.isdir(challenge_set_path):
                continue

            for slot in os.listdir(challenge_set_path):
                slot_path = os.path.join(challenge_set_path, slot)
                if not os.path.isdir(slot_path):
                    continue

                for file_name in os.listdir(slot_path):
                    if file_name.endswith('.tsv'):
                        system_name = file_name[:-4]  # remove .tsv
                        system_names.add(system_name)
                        file_path = os.path.join(slot_path, file_name)

                        with open(file_path, mode='r', encoding='utf-8') as f:
                            reader = csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE, quotechar=None)
                            row_count = sum(1 for _ in reader)

                        summary_data[challenge_set_name][system_name] += row_count

        # Write summary TSV
        system_names = sorted(system_names)
        with open(summary_output_path, mode='w', encoding='utf-8', newline='') as out_file:
            writer = csv.writer(out_file, delimiter='\t', quoting=csv.QUOTE_MINIMAL, quotechar='"')
            header = ['challenge_set_name'] + system_names
            writer.writerow(header)

            for challenge_set_name in sorted(summary_data.keys()):
                row = [challenge_set_name]
                for system_name in system_names:
                    row.append(str(summary_data[challenge_set_name].get(system_name, 0)))
                writer.writerow(row)


def main():
    """
    Main function to parse arguments and initiate processing.
    """
    parser = argparse.ArgumentParser(description="Process segment TSV files based on submission details.")
    parser.add_argument('--input_dir', required=True, help='Directory containing the segment files.')
    parser.add_argument('--output_dir', required=True, help='Directory to save the output TSV files.')
    parser.add_argument('--submission_details_tsv', required=True, help='TSV file with submission details.')

    args = parser.parse_args()

    processor = SubmissionProcessor(
        input_directory=args.input_dir,
        output_directory=args.output_dir,
        submission_details_tsv=args.submission_details_tsv
    )
    processor.process_all()
    print("Processing completed successfully.")

if __name__ == '__main__':
    main()