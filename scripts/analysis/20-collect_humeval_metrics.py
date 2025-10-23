# %%

import csv
import glob
import json
import collections

with open("../../../wmt25-general-mt/data/wmt25-genmt-humeval.jsonl", "r") as f:
    data_humeval = [json.loads(line) for line in f]
    for line in data_humeval:
        line["metrics"] = collections.defaultdict(dict)
    data_humeval = {
        item["doc_id"]: item for item in data_humeval
    }

for fname in glob.glob("../../data/all-task1-submissions/*.tsv"):
    if ".sys." in fname:
        continue
    metric_name = fname.rsplit("/", 1)[1].split(".", 1)[0]
    print(metric_name)
    with open(fname, "r") as f:
        data = list(csv.DictReader(f, delimiter="\t"))
        doc_seg_counter = collections.Counter()
        for line in data:
            if line["set_id"] != "official":
                continue
            seg_id = doc_seg_counter[(line["doc_id"], line["system_id"])]
            doc_seg_counter[(line["doc_id"], line["system_id"])] += 1
            # non-human-evaluated segments are skipped
            if f"{line['doc_id']}_#_{seg_id}" not in data_humeval:
                continue
            data_humeval[f"{line['doc_id']}_#_{seg_id}"]["metrics"][line["system_id"]][metric_name] = float(line["overall"])

with open("../../data/wmt25-genmt-humeval-metrics.jsonl", "w") as f:
    for item in data_humeval.values():
        f.write(json.dumps(item, ensure_ascii=False) + "\n")