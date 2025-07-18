import os
import zipfile
import shutil
import pathlib

# Lists of IDs to exclude and prioritize
EXCLUDE_IDS = [78032, 78033, 78028, 79093, 79098, 78703]  # Test submissions
PRIMARY_IDS = []

# Directories
SOURCE_DIR = "/home/elav01/Documents/DFKI/SLT/publications/2024/WMT24/challenge sets/metrics24_submissions"
INTERMEDIATE_DIR = "/home/elav01/Documents/DFKI/SLT/publications/2024/WMT24/challenge sets/metrics24_submissions_unzipped"
FINAL_DIR = "/home/elav01/PycharmProjects/wmt24-metrics/wmt24metrics_challengeset_preproc/data/3-scored"


def extract_zips(source_dir, intermediate_dir):
    # Create the intermediate directory if it doesn't exist
    if not os.path.exists(intermediate_dir):
        os.makedirs(intermediate_dir)

    submissions_per_metric = {}

    # Traverse all subdirectories in the source directory
    for root, _, files in os.walk(source_dir):
        for zip_filename in files:
            # Process only zip files
            if zip_filename.endswith('.zip'):
                metric_name, submission_id = get_submission_id_and_name_from_filename(zip_filename)

                # Skip files with IDs in the EXCLUDE_IDS list
                if submission_id in EXCLUDE_IDS:
                    continue

                # Group files by their base name (excluding the leading ID)
                if metric_name not in submissions_per_metric:
                    submissions_per_metric[metric_name] = []
                submissions_per_metric[metric_name].append((submission_id, os.path.join(root, zip_filename)))

    # Process each group of files with the same base name
    for metric_name, files in submissions_per_metric.items():
        primary_file = None
        # Check if any file in the group is in the PRIMARY_IDS list
        for submission_id, path in files:
            if submission_id in PRIMARY_IDS:
                primary_file = path
                files = [(submission_id, primary_file)]
                break
        # # If a primary file is found, use only that file
        # if primary_file:

        # Extract each zip file into its own directory within the intermediate directory
        for submission_id, path in files:
            dirname = os.path.splitext(os.path.basename(path))[0]
            extract_path = os.path.join(intermediate_dir, dirname)
            with zipfile.ZipFile(path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            print(f"Extracted {path} into {extract_path}")


def get_submission_id_and_name_from_filename(zip_filename):
    parts = zip_filename.split('_')
    # Skip files that do not start with a numerical ID followed by an underscore
    if len(parts) < 2 or not parts[0].isdigit():
        zip_id = None
    else:
        zip_id = int(parts[0])
    base_name = '_'.join(parts[1:])
    return base_name, zip_id


def compare_files_and_prepare_final(intermediate_dir, final_dir):
    # Create the final directory if it doesn't exist
    if not os.path.exists(final_dir):
        os.makedirs(final_dir)

    file_map = {}
    # Traverse all subdirectories in the intermediate directory
    for subdir, _, files in os.walk(intermediate_dir):
        for file in files:
            # Group files by their name
            if file not in file_map:
                file_map[file] = []
            file_map[file].append(os.path.join(subdir, file))

    # Compare files with the same name across different directories
    for filename, paths in file_map.items():
        if len(paths) == 1:
            path = paths[0]
            original_zip = os.path.basename(os.path.dirname(path))
            metric_name, submission_id = get_submission_id_and_name_from_filename(original_zip)
            new_filename = f"{metric_name}.{filename.split('.', 1)[1]}"
            new_filename = new_filename.replace("_MACOSX._", "")
            new_path = os.path.join(final_dir, new_filename)
            shutil.copy2(path, new_path)
            print(f"Copied {path} to {new_path}")
        elif len(paths) > 1:
            diff_count = 0

            for i in range(len(paths) - 1):
                try:
                    with open(paths[i], 'r') as file1, open(paths[i + 1], 'r') as file2:
                        diff = sum(1 for line1, line2 in zip(file1, file2) if line1 != line2)
                        filename1 = pathlib.PurePath(paths[i]).parent.name
                        filename2 = pathlib.PurePath(paths[i+1]).parent.name
                        print(f"  >>  File: {filename}, {filename1}/{filename2}, Differences: {diff} lines")
                        diff_count += diff
                except UnicodeDecodeError as e:
                    print(e)
                    diff_count += 1
                    pass

            # If there are differences, rename and copy the files to the final directory
            if diff_count > 0:
                for path in paths:
                    original_zip = os.path.basename(os.path.dirname(path))
                    metric_name, submission_id = get_submission_id_and_name_from_filename(original_zip)
                    new_filename = f"{metric_name}_{submission_id}.{filename.split('.', 1)[1]}"
                    new_filename = new_filename.replace("_MACOSX._", "")
                    new_path = os.path.join(final_dir, new_filename)
                    shutil.copy2(path, new_path)
                    print(f"** Copied and renamed {path} to {new_path}")
            elif diff_count == 0:
                path = paths[0]
                original_zip = os.path.basename(os.path.dirname(path))
                metric_name, submission_id = get_submission_id_and_name_from_filename(original_zip)
                new_filename = f"{metric_name}.{filename.split('.', 1)[1]}"
                new_filename = new_filename.replace("_MACOSX._", "")
                new_path = os.path.join(final_dir, new_filename)
                shutil.copy2(path, new_path)
                print(f"Copied {path} to {new_path}")

if __name__ == "__main__":
    extract_zips(SOURCE_DIR, INTERMEDIATE_DIR)
    compare_files_and_prepare_final(INTERMEDIATE_DIR, FINAL_DIR)
    # shutil.rmtree(INTERMEDIATE_DIR)