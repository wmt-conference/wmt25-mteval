#!/usr/bin/env python3
# Assuming data from wmt-conference/wmt25-general-mt is downloaded 
# Command to run: 
# python3 testset_jsonl_to_tsv.py  \
#     --src-file wmt25-general-mt/data/wmt25-genmt.jsonl  \
#     --teams-file wmt25-general-mt/data/systems_metadata.json \
#     --hyp-dir wmt25-general-mt/data/systems \
#     --output-path wmt25_metrics_testset.tsv

import argparse
import collections
import json
import os.path
import re
import sys
import csv


# TODO: remove submissions that won't be sent to human eval (ask Tom/Vilém)

# Parts of an official test segment derived from each resource:
SrcSeg = collections.namedtuple("SrcSeg", ["doc_id", "segment_id", "source_lang", "target_lang", "set_id", "source_segment", "reference_segment", "domain_name", "method"])
Team = collections.namedtuple("Team", ["system_id", "x_hyp_file"])

Segment = collections.namedtuple("Segment", ["doc_id", "segment_id", "source_lang", "target_lang", "set_id", "system_id", "source_segment", "hypothesis_segment", "reference_segment", "domain_name", "method"])

NEEDED_SRC_FIELDS = ["src_lang", "tgt_lang", "doc_id", "domain", "src_text"]
NEEDED_HYP_FIELDS = ["doc_id", "hypothesis"]

# Language pairs:
def make_lp_name(src_lang, tgt_lang):
    return f"{src_lang}{tgt_lang}"
ESA_LANGS = [("cs", "de_DE"), ("cs", "uk_UA"), ("en", "ar_EG"), ("en", "bho_IN"), ("en", "zh_CN"), ("en", "cs_CZ"), ("en", "et_EE"), ("en", "is_IS"), ("en", "it_IT"), ("en", "ja_JP"), ("en", "mas_KE"), ("en", "ru_RU"), ("en", "sr_Cyrl_RS"), ("en", "uk_UA")]
MQM_LANGS = [("en", "ko_KR"), ("ja", "zh_CN")]
METHOD = dict([ (make_lp_name(tup[0], tup[1]), "ESA") for tup in ESA_LANGS ] +
              [ (make_lp_name(tup[0], tup[1]), "MQM") for tup in MQM_LANGS ])


def load_source(filename):
    """
    Reads a file of JSON lines representing the WMT General (document-level)
    test set and extracts it to a collection of SrcSeg tuples, each of which
    represents one paragraph-level segment found.  The returned object is a
    dictionary mapping a language pair (e.g. "enja_JP") to a dictionary mapping
    a document ID to a list of SrcSegs.  Note that language codes are copied
    directly from the input.
    """

    counters_by_lp = dict()
    segs_by_lp_and_doc = dict()  # dict of dict of list

    sys.stderr.write(f"\nReading source documents from file {filename}\n")
    with open(filename, encoding="utf-8") as fh:
        for line in fh:
            doc_data = json.loads(line)

            # Skip test suites:
            if not is_official_test_set(doc_data):
                continue
            
            # Verify that all necessary fields are filled in:
            if not fields_exist(doc_data, NEEDED_SRC_FIELDS):
                raise ValueError(f"All needed JSON fields {NEEDED_SRC_FIELDS} aren't present; unable to extract document {doc_data}")

            # Skip lang pairs that aren't going to be human-evaluated:
            lp = make_lp_name(doc_data["src_lang"], doc_data["tgt_lang"])
            if not is_official_lp(lp):
                continue

            # Split source and reference document text into paragraph segments:
            src_texts = segment_text(doc_data["src_text"])
            ref_texts = []
            if "refs" in doc_data and "refA" in doc_data["refs"]:
                ref_texts = segment_text(doc_data["refs"]["refA"]["ref"])
            src_len = len(src_texts)
            ref_len = len(ref_texts)
            if src_len > 0 and ref_len > 0 and ref_len != src_len:
                raise ValueError(f"Reference has wrong number of segments ({ref_len}, should be {src_len}); unable to extract document {doc_data}")

            # Save the segments found:
            segs_for_doc = list()
            for i in range(len(src_texts)):
                # Make an ID for this segment within its language pair:
                if lp not in counters_by_lp:
                    counters_by_lp[lp] = 0
                seg_id = counters_by_lp[lp]
                counters_by_lp[lp] += 1

                # Create and store the source segment within its document:
                st = trim_and_escape(src_texts[i])
                rt = trim_and_escape(ref_texts[i]) if ref_texts else ""
                seg = SrcSeg(doc_id=doc_data["doc_id"],
                             segment_id=str(seg_id),
                             source_lang=doc_data["src_lang"],
                             target_lang=doc_data["tgt_lang"],
                             set_id="official",
                             source_segment=st,
                             reference_segment=rt,
                             domain_name=doc_data["domain"],
                             method=METHOD[lp])
                segs_for_doc.append(seg)

            # Store the segments for this document within its lang pair:
            if lp not in segs_by_lp_and_doc:
                segs_by_lp_and_doc[lp] = dict()
            doc_id = doc_data["doc_id"]
            if doc_id in segs_by_lp_and_doc[lp]:
                raise ValueError()
            segs_by_lp_and_doc[lp][doc_id] = segs_for_doc

    # Report back what we created:
    for lp in segs_by_lp_and_doc:
        num_segs = sum([ len(segs_by_lp_and_doc[lp][doc]) for doc in segs_by_lp_and_doc[lp] ])
        sys.stderr.write(f"Loaded {num_segs} source segments for {lp}\n")
    return segs_by_lp_and_doc


def load_teams(filename):
    """
    Reads a JSON file containing information about the WMT General MT
    participants and extracts it to a collection of Team tuples, each of which
    represents one primary submission found.  Returns the list of Teams.
    """
    
    sys.stderr.write(f"\nReading team information from file {filename}\n")
    with open(filename, encoding="utf-8") as fh:
        team_data = json.load(fh)

    # Create a Team for each team found:
    teams = list()
    for team_entry in team_data:
        team = Team(system_id=team_entry,
                    x_hyp_file=f"{team_entry}.jsonl")
        teams.append(team)

    # Report back what we created:
    sys.stderr.write(f"Loaded {len(teams)} teams\n")
    return teams


def load_submission(filename):
    """
    Reads a file of JSON lines representing an MT translation of the WMT
    General (document-level) test set and extracts it to a collection of
    structures, each of which represents one document found.  The returned
    object is a dictionary mapping a language pair (e.g. "enja_JP") to a list
    of Python-interpreted JSON structures.  Note that language codes are
    inferred directly from the input.
    """

    docs_by_lp = dict()
    sys.stderr.write(f"\nReading hypothesis documents from file {filename}\n")
    with open(filename, encoding="utf-8") as fh:
        for line in fh:
            doc_data = json.loads(line)

            # Skip test suites:
            #if not is_official_test_set(doc_data):
            #    continue

            # Verify that all necessary fields are filled in:
            if not fields_exist(doc_data, NEEDED_HYP_FIELDS, blanks_ok=True):
                raise ValueError(f"All needed JSON fields {NEEDED_HYP_FIELDS} aren't present; unable to extract document {doc_data}")

            # Skip lang pairs that aren't going to be human-evaluated:
            lp = infer_lp_name(doc_data)
            if not is_official_lp(lp):
                continue

            # Store this document:
            if lp not in docs_by_lp:
                docs_by_lp[lp] = list()
            docs_by_lp[lp].append(doc_data)

    sys.stderr.write(f"Loaded documents for {len(docs_by_lp)} official lang pairs\n")
    return docs_by_lp


def unify_src_hyp(src_segs_by_lp_and_doc, hyp_docs_by_lp,
                  system_id):
    """
    x
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


def is_official_test_set(doc_data):
    return "collection_id" in doc_data and doc_data["collection_id"] == "general"


def fields_exist(doc_data, needed_fields, blanks_ok=False):
    success = True
    for field in needed_fields:
        if field not in doc_data:
            success = False
            break
        if not doc_data[field] and not blanks_ok:
            success = False
            break
    return success


def segment_text(doc_text):
    return doc_text.split("\n\n")


NEWLINES_REGEX = re.compile("\\s*\n\\s*")

def trim_and_escape(text):
    fixed = text.strip().replace("\t", " ")
    # there are literal tabs, not sure if we would want to replace them too though
    if "    " in fixed:
        fixed = fixed.replace("    ", " ")
    return NEWLINES_REGEX.sub(r" \\n ", fixed)


# Map from target language to the source languages it's paired with:
SL_BY_TL = dict()
for (sl, tl) in ESA_LANGS + MQM_LANGS:
    if tl not in SL_BY_TL:
        SL_BY_TL[tl] = list()
    SL_BY_TL[tl].append(sl)

def infer_lp_name(doc_data):
    if fields_exist(doc_data, ["src_lang", "tgt_lang"]):
        return make_lp_name(doc_data["src_lang"], doc_data["tgt_lang"])
    elif fields_exist(doc_data, ["tgt_lang"]):
        tl = doc_data["tgt_lang"]
        if tl in SL_BY_TL and len(SL_BY_TL[tl]) == 1:
            return make_lp_name(SL_BY_TL[tl][0], tl)
    elif fields_exist(doc_data, ["doc_id"]):
        (sl, tl) = doc_data["doc_id"].split("_#_")[0].split("-")
        return make_lp_name(sl, tl)
    else:
        raise ValueError(f"Can't find or infer language pair from document {doc_data}")


def is_official_lp(lp):
    return lp in METHOD
    

def main():
    # Define and get command-line arguments:
    parser = argparse.ArgumentParser(description="x")
    parser.add_argument("--src-file", type=str, required=True,
                        help="Location of the JSON lines file containing the source side of the test data")
    parser.add_argument("--teams-file", type=str, required=True,
                        help="Location of the JSON file containing data about the participating MT teams and their output files")
    parser.add_argument("--hyp-dir", type=str, required=True,
                        help="Location of the directory containing the teams' output files in JSON lines format")
    parser.add_argument("--output-path", type=str, required=True,
                        help="Location to save the tsv file")
    args = parser.parse_args()

    # Short circuit: don't start work if MT hyps location is invalid:
    if not os.path.isdir(args.hyp_dir):
        raise ValueError(f"Provided directory of MT hypothesis files doesn't seem to be a directory: {args.hyp_dir}")

    # Extract source segments:
    src_segs_by_lp_and_doc = load_source(args.src_file)

    # Match each MT output to source segments; accumulate results by lang pair:
    teams = load_teams(args.teams_file)
    complete_segs_by_lp = dict()
    for team in teams:
        subm_path = os.path.join(args.hyp_dir, team.x_hyp_file)
        if not os.path.isfile(subm_path):
            sys.stderr.write(f"\nERROR: Submission file {subm_path} not found; skipping it!\n")
        else:
            hyp_docs_by_lp = load_submission(subm_path)
            hyp_segs_by_lp = unify_src_hyp(src_segs_by_lp_and_doc, hyp_docs_by_lp,
                                           team.system_id)
            for lp in hyp_segs_by_lp:
                if lp not in complete_segs_by_lp:
                    complete_segs_by_lp[lp] = list()
                complete_segs_by_lp[lp] += hyp_segs_by_lp[lp]

    # Write accumulated results out by lang pair:
    count = 0
    try:
        with open(args.output_path, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
            if hasattr(Segment, '_fields'):
                writer.writerow(Segment._fields)
            else:
                print("Warning: Segment._fields not found. Skipping header.")
            for lp, segments in complete_segs_by_lp.items():
                if segments:
                    for seg in segments:
                        if seg is not None:
                            count += 1
                            sanitized_seg = []
                            for field in seg:
                                if isinstance(field, str):
                                    sanitized_seg.append(field)
                                elif field is None:
                                    sanitized_seg.append('') # Replace None with empty string
                                else:
                                    sanitized_seg.append(str(field))
                            writer.writerow(sanitized_seg)
                        else:
                            print(f"Warning: Encountered a None segment in {lp}")

        print(f"Successfully wrote {count} segments to {args.output_path}")

    except AttributeError as e:
        print(f"AttributeError: {e}. Check Segment definition and attributes.")
    except TypeError as e:
        print(f"TypeError during writing: {e}. Check data types within segments.")
    except Exception as e:
        print(f"An error occurred: {e}")
    

if __name__ == "__main__":
    main()
