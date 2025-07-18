import os
import shutil

from tqdm import tqdm

# Constants
SOURCE_DIR = 'data/3-scored'
TARGET_DIR = 'data/4-to_return'


def process_files():
    # Ensure the target directory exists
    os.makedirs(TARGET_DIR, exist_ok=True)

    # Iterate over all files in the source directory
    for filename in tqdm(sorted(os.listdir(SOURCE_DIR)), desc='metrics', position=0):
        if filename.endswith('.score'):
            source_file_path = os.path.join(SOURCE_DIR, filename)

            # Read the file and process lines
            with open(source_file_path, 'r', encoding="utf8", errors="surrogateescape") as file:
                lines = file.readlines()

            open_target_files = {}
            # Process each line
            # for line in tqdm(lines, desc='files', position=1, leave=False):
            for line in lines:
                columns = line.strip().split('\t')
                if len(columns) > 2 and columns[2].startswith('challenge_'):
                    challengeset_name = columns[2].split('_')[1]
                    target_subdir = os.path.join(TARGET_DIR, challengeset_name)
                    os.makedirs(target_subdir, exist_ok=True)

                    target_file_path = os.path.join(target_subdir, filename)
                    if target_file_path not in open_target_files:
                        open_target_files[target_file_path] = open(target_file_path, 'w')

                    # Write the processed line to the target file
                    target_file = open_target_files[target_file_path]
                    tsv_columns = '\t'.join(columns[:2] + columns[3:])
                    target_file.write(f"{tsv_columns}\n")

            for file in open_target_files.values():
                file.close()


if __name__ == '__main__':
    process_files()
