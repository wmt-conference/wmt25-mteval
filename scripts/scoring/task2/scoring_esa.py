#!/usr/bin/env python3

import sys
import collections
import logging
import operator
import os
import statistics
import pandas as pd
import numpy as np

TSV_FIELDS_RELEASE = [
    "doc_id",
    "segment_id",
    "source_lang",
    "target_lang",
    "set_id",
    "system_id",
    "source_segment",
    "hypothesis_segment",
    "reference_segment",
    "domain_name",
    "method",
]

TSV_FIELDS_GOLD = ["start_indices", "end_indices", "error_types"]

def get_counts(ex, len_hyp):
    major = np.zeros(len_hyp)
    minor = np.zeros(len_hyp)
    for er in ex:
        if er["start"] == "missing":
            continue
        if er["severity"] == "undecided":
            continue
        if er["severity"] in ["major", "critical"]:
            counts = major
        elif er["severity"] == "minor":
            counts = minor
        else:
            print(er)
            raise ValueError(f"Unknown severity: {er['severity']}")
        counts[int(er["start"]) : int(er["end"])] += 1
    return major, minor


def prec_rec_f1(both_count, gold_count, pred_count) -> tuple[float, float, float]:
    p = both_count / pred_count if pred_count else 1.0
    r = both_count / gold_count if gold_count else 1.0
    f1 = (2 * p * r) / (p + r) if p + r else 0.0
    return p, r, f1


def get_char_f1(len_hypothesis, errors_gold, errors_pred, partial_credit=0.5):

    tp = 0
    total_gold, total_pred = 0, 0
    for x, y, z in zip(errors_gold, errors_pred, len_hypothesis):
        gold_major_counts, gold_minor_counts = get_counts(x, z)
        pred_major_counts, pred_minor_counts = get_counts(y, z)

        total_gold += gold_major_counts.sum() + gold_minor_counts.sum()
        total_pred += pred_major_counts.sum() + pred_minor_counts.sum()

        for c_gold_maj, c_pred_maj, c_gold_min, c_pred_min in zip(
            gold_major_counts,
            pred_major_counts,
            gold_minor_counts,
            pred_minor_counts,
        ):
            # Full credit given for each correctly predicted major and minor error.
            tp += min(c_gold_maj, c_pred_maj)
            tp += min(c_gold_min, c_pred_min)

            # Partial credit given for errors that aren't the right severity.
            c_gold_unmatched = max(0, c_gold_maj - c_pred_maj) + max(
                0, c_gold_min - c_pred_min
            )
            c_pred_unmatched = max(0, c_pred_maj - c_gold_maj) + max(
                0, c_pred_min - c_gold_min
            )
            tp += min(c_gold_unmatched, c_pred_unmatched) * partial_credit

    p, r, f1 = prec_rec_f1(tp, total_gold, total_pred)
    return p, r, f1


def get_error_list(x):
    if x["error_types"] == "no-error":
        return []
    else:
        start_indices = x["start_indices"].split(" ")
        end_indices = x["end_indices"].split(" ")
        error_type = x["error_types"].split(" ")

        errors = []
        for x, y, z in zip(start_indices, end_indices, error_type):
            if not x or not y or not z:
                logging.warn("Warning: Missing or empty start_indices, end_indices, or error_types for a non 'no-error' case.")
                return []
            errors.append({"start": x, "end": y, "severity": z})

        return errors


def main():
    # Set logging properties:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(asctime)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    [_, input_dir, output_dir] = sys.argv
    reference_dir = os.path.join(input_dir, "ref")
    submission_dir = os.path.join(input_dir, "res")
    submission_file_name = "predictions.tsv"

    predictions_data = pd.read_csv(
        os.path.join(submission_dir, submission_file_name),
        sep="\t",
        keep_default_na=False,
    )
    gold_data = pd.read_csv(
        os.path.join(reference_dir, "task2_refs.tsv"),
        sep="\t",
        keep_default_na=False,
    )

    gold_data["lp"] = gold_data["source_lang"] + "-" + gold_data["target_lang"]
    predictions_data["lp"] = (
        predictions_data["source_lang"] + "-" + predictions_data["target_lang"]
    )

    common_lps = set(predictions_data["lp"].unique()) & set(gold_data["lp"].unique())
    common_lps_name = (" ").join(common_lps)
    logging.info(f"=== Submissions read for language pairs {common_lps_name} ===")

    final_score_lines = []
    all_scores = []
    for lp in common_lps:
        logging.info(f"Getting errors for pred for {lp}")
        pred_lp = predictions_data[predictions_data["lp"] == lp].copy()
        pred_lp["errors"] = pred_lp.apply(get_error_list, axis=1)
        
        logging.info(f"Getting errors for gold for {lp}")
        gold_lp = gold_data[gold_data["lp"] == lp].copy()
        gold_lp["errors"] = gold_lp.apply(get_error_list, axis=1)
        gold_lp["len_hyp"] = gold_lp["hypothesis_segment"].apply(lambda x: len(x))

        logging.info("Scoring only the official set for leaderboard")
        pred_lp = pred_lp[pred_lp.set_id.isin(["official"])]
        gold_lp = gold_lp[gold_lp.set_id.isin(["official"])]

        assert len(pred_lp) == len(gold_lp), f"Length mismatch: len(pred_lp) is {len(pred_lp)}, but len(gold_lp) is {len(gold_lp)}"
        
        merged_lp = pred_lp.merge(
            gold_lp, on=[ "doc_id",  "segment_id", "source_lang", "target_lang", "set_id", "system_id", "domain_name", "method"], how="left", suffixes=("_pred", "_gold")
        )
        assert len(merged_lp) == len(pred_lp), f"Length mismatch: len(merged_lp) is {len(merged_lp)}, but len(pred_lp) is {len(pred_lp)}"

        precision, recall, f1 = get_char_f1(
            merged_lp["len_hyp"].to_list(),
            merged_lp["errors_gold"].to_list(),
            merged_lp["errors_pred"].to_list(),
            partial_credit=0.5,
        )
        final_score_lines.append(lp.replace("-", "") + "_f1: {:.4}".format(f1))
        final_score_lines.append(lp.replace("-", "") + "_rec: {:.4}".format(recall))
        final_score_lines.append(lp.replace("-", "") + "_prec: {:.4}".format(precision))
        all_scores.append([precision, recall, f1])

    average_scores = np.mean(np.array(all_scores), axis=0)
    final_score_lines.append("avg_f1: {:.4}".format(average_scores[2]))
    final_score_lines.append("avg_rec: {:.4}".format(average_scores[0]))
    final_score_lines.append("avg_prec: {:.4}".format(average_scores[1]))

    with open(os.path.join(output_dir, "scores.txt"), "w", encoding="utf-8") as wf:
        for line in final_score_lines:
            wf.write(line + "\n")


if __name__ == "__main__":
    main()
