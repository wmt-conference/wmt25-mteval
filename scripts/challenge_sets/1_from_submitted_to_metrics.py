import os
import shutil

# Define input and output directories
INPUT_DIRECTORY = 'data/1-submitted'
OUTPUT_DIRECTORY = 'data/2-to_metrics'

# Define the dictionaries for mapping
CHALLENG_SET_NAME_MAP = {
    'AfriMTE-ade-devtest-v2': 'AfriMTE',
    'bio-mqm-dataset': 'bioMQM',
}

LANG_CODE_MAP = {
    'eng': 'en',
    'fra': 'fr',
    # Add more mappings as needed
}


# Function to rename files
def rename_file(filename):
    parts = filename.split('.')
    challenge_set_name = parts[0]
    source_lang_code, target_lang_code = parts[1].split('-')
    file_type = parts[2]

    shortened_challenge_set_name = CHALLENG_SET_NAME_MAP.get(challenge_set_name, challenge_set_name)
    shortened_source_lang_code = LANG_CODE_MAP.get(source_lang_code, source_lang_code)
    shortened_target_lang_code = LANG_CODE_MAP.get(target_lang_code, target_lang_code)

    if 'hyp-' in file_type:
        system_name = file_type.split('-')[1]
        new_file_type = f'hyp.{system_name}'
    else:
        new_file_type = file_type

    if file_type == 'src':
        new_filename = f"challenge_{shortened_challenge_set_name}.{shortened_source_lang_code}-{shortened_target_lang_code}.{new_file_type}.{shortened_source_lang_code}"
    elif file_type == 'docID':
        new_filename = f"challenge_{shortened_challenge_set_name}.{shortened_source_lang_code}-{shortened_target_lang_code}.{new_file_type}.csv"
    else:
        new_filename = f"challenge_{shortened_challenge_set_name}.{shortened_source_lang_code}-{shortened_target_lang_code}.{new_file_type}.{shortened_target_lang_code}"

    return new_filename


if __name__ == '__main__':
    # Create output subdirectories if they don't exist
    os.makedirs(os.path.join(OUTPUT_DIRECTORY, 'references'), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIRECTORY, 'sources'), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIRECTORY, 'metadata'), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIRECTORY, 'system_outputs'), exist_ok=True)

    # Process files in the first level of subdirectories
    for subdir in next(os.walk(INPUT_DIRECTORY))[1]:
        subdir_path = os.path.join(INPUT_DIRECTORY, subdir)
        for file in os.listdir(subdir_path):
            file_path = os.path.join(subdir_path, file)
            if os.path.isfile(file_path):
                if file.endswith('ref.txt'):
                    new_filename = rename_file(file)
                    shutil.copy(file_path, os.path.join(OUTPUT_DIRECTORY, 'references', new_filename))
                elif file.endswith('src.txt'):
                    new_filename = rename_file(file)
                    shutil.copy(file_path, os.path.join(OUTPUT_DIRECTORY, 'sources', new_filename))
                elif file.endswith("docID.txt"):
                    new_filename = rename_file(file)
                    shutil.copy(file_path, os.path.join(OUTPUT_DIRECTORY, 'metadata', new_filename))
                elif 'hyp-' in file and file.endswith('.txt'):
                    new_filename = rename_file(file)
                    shutil.copy(file_path, os.path.join(OUTPUT_DIRECTORY, 'system_outputs', new_filename))
