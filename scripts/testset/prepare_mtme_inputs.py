from testset_jsonl_to_tsv_task1 import load_source, load_submission, load_teams
import os
import sys
from testset_jsonl_to_tsv_task1 import segment_text, trim_and_escape, Segment

GENMT_DATA_DIR="../../wmt25-general-mt"
MAIN_OUT_DIR="../data/metrics_inputs/txt/generaltest2025"
SOURCE_DIR = MAIN_OUT_DIR + "/sources"
SYSOUTS_DIR = MAIN_OUT_DIR + "/system_outputs"
REFERENCES_DIR = MAIN_OUT_DIR + "/references"
METADATA_DIR = MAIN_OUT_DIR + "/metadata"
TEST_NAME = "generaltest2025"

os.makedirs(SOURCE_DIR, exist_ok=True)
os.makedirs(SYSOUTS_DIR, exist_ok=True)
os.makedirs(REFERENCES_DIR, exist_ok=True)
os.makedirs(METADATA_DIR, exist_ok=True)

def unify_src_hyp(src_segs_by_lp_and_doc, hyp_docs_by_lp, system_id):
    """
    taken from testset_jsonl_to_tsv_task1.py but removes any filtering of documents to preserve all documents. 
    """

    complete_segs_by_lp = dict()
    sys.stderr.write(f"Aligning submission {system_id}\n")
    
    # Submission decides which lang pairs it attempts:
    for lp in hyp_docs_by_lp:

        src_segs_by_doc = src_segs_by_lp_and_doc[lp]
        hyp_texts_by_doc = { doc["doc_id"]: doc["hypothesis"] for doc in hyp_docs_by_lp[lp] }
        lp_complete_segs = list()
        lp_success = True

        # Source decides which documents must exist in this lang pair:
        for doc_id in src_segs_by_doc:
            # Check that the submission's document appears to match the source:
            if doc_id not in hyp_texts_by_doc:
                sys.stderr.write(f"ERROR: Expected document {doc_id} missing from submission {system_id} for {lp}\n")
                lp_success = False
                break
            hyp_texts = segment_text(hyp_texts_by_doc[doc_id])
            src_len = len(src_segs_by_doc[doc_id])
            hyp_len = len(hyp_texts)
            if hyp_len != src_len:
                sys.stderr.write(f"ERROR: Submission {system_id} for {lp} has wrong number of segments ({hyp_len}) for document {doc_id} (should be {src_len})\n")
                lp_success = False
                break

            # Create and store complete segments from the aligned document:
            for src_seg, hyp_text in zip(src_segs_by_doc[doc_id], hyp_texts):
                params = src_seg._asdict()
                params["system_id"] = system_id
                params["hypothesis_segment"] = trim_and_escape(hyp_text)
                seg = Segment(**params)
                lp_complete_segs.append(seg)

        # Report progress at the end of processing each lang pair:
        if lp_success:
            sys.stderr.write(f"Extracted {len(lp_complete_segs)} hyp segments for {lp}\n")
            complete_segs_by_lp[lp] = lp_complete_segs
        else:
            sys.stderr.write(f"Skipping {lp} because of errors\n")

    # Return the whole submission's worth of complete segments:
    sys.stderr.write(f"Extracted complete segments for {len(complete_segs_by_lp)} lang pairs\n")
    return complete_segs_by_lp


src_segs_by_lp_and_doc = load_source(f"{GENMT_DATA_DIR}/data/wmt25-genmt.jsonl")
teams = load_teams(f"{GENMT_DATA_DIR}/data/systems_metadata_updated3.json")

complete_segs_by_lp = dict()
for team in teams:
    subm_path = os.path.join(f"{GENMT_DATA_DIR}/data/systems", team.x_hyp_file)
    if not os.path.isfile(subm_path):
        sys.stderr.write(f"\nERROR: Submission file {subm_path} not found; skipping it!\n")
    else:
        hyp_docs_by_lp = load_submission(subm_path)
        hyp_segs_by_lp = unify_src_hyp(src_segs_by_lp_and_doc, hyp_docs_by_lp,
                                        team.system_id)
        for lp in hyp_segs_by_lp:
            if lp not in complete_segs_by_lp:
                complete_segs_by_lp[lp] = {}
            complete_segs_by_lp[lp][team.system_id] = hyp_segs_by_lp[lp]
        

for lp in complete_segs_by_lp:
    systems = list(complete_segs_by_lp[lp].keys())
    src_lang, tgt_lang = lp.split("-")
    
    sources = [x.source_segment for x in complete_segs_by_lp[lp][systems[0]]]
    references = [x.reference_segment for x in complete_segs_by_lp[lp][systems[0]] if x.reference_segment!='']
    domains = [x.domain_name  for x in complete_segs_by_lp[lp][systems[0]]]  
    doc_ids = [x.doc_id for x in complete_segs_by_lp[lp][systems[0]]]
    
    # write sources
    with open(f"{SOURCE_DIR}/{TEST_NAME}.{lp}.src.{src_lang}", "w") as f:
        for source in sources:
            f.write(source+"\n")
            
    # write references
    if len(references)> 0:
        with open(f"{REFERENCES_DIR}/{TEST_NAME}.{lp}.ref.refA.{tgt_lang}", "w") as f:
            for reference in references:
                f.write(reference+"\n")
                
    # write system outputs
    for sys in complete_segs_by_lp[lp]:
        system_outputs = [x.hypothesis_segment for x in complete_segs_by_lp[lp][sys]]
        with open(f"{SYSOUTS_DIR}/{TEST_NAME}.{lp}.hyp.{sys}.{tgt_lang}", "w") as f:
            for out in system_outputs:
                f.write(out+"\n")
     
    # write metadata
    with open(f"{METADATA_DIR}/{lp}.tsv", "w") as f:
        for (x,y) in zip(domains, doc_ids):
            f.write(f"{x}\t{y}\n")
    