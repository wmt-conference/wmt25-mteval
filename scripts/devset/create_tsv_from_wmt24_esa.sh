#!/bin/bash

set -e

if ! command -v pipx &> /dev/null; then
    pip install pipx --user
    pipx ensurepath
fi

if ! command -v uv &> /dev/null; then
    pipx install uv
fi

# Create a tsv format file for wmt24_esa file from wmt24_esa.jsonl
WMT24_ESA_JSONL=wmt24_esa.jsonl
if [ ! -f $WMT24_ESA_JSONL ]; then
    wget https://github.com/wmt-conference/wmt24-news-systems/raw/refs/heads/main/jsonl/wmt24_esa.jsonl
fi

WMT24_DATA_DIR=data/devset/
DEV_TSV=$WMT24_DATA_DIR/mteval-task2-dev.tsv
mkdir -p $WMT24_DATA_DIR

uv run --python 3.11 \
    --with pandas \
    --with datasets \
    scripts/devset/create_tsv_from_wmt24_esa.py \
    --wmt24_esa_jsonl $WMT24_ESA_JSONL \
    --output_tsv $DEV_TSV \
    --filter_data_with_invalid_span
