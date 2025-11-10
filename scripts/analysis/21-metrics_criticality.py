# %%

import matplotlib.pyplot as plt
import json
import statistics
import os
import tqdm

os.makedirs("../../generated", exist_ok=True)

with open("../../data/wmt25-genmt-humeval-metrics.jsonl", "r") as f:
    data = [json.loads(line) for line in f]

for line in data:
    line["scores_avg"] = {}
    # average human1 and human2
    for sys, sys_v in line["scores"].items():
        line["scores_avg"][sys] = statistics.mean([x["score"] for x in sys_v])

# %%
plt.rcParams["font.family"] = "serif"

fig, axs = plt.subplots(2, 7, figsize=(9, 3), sharey=True)
langs_all = list({x["doc_id"].split("_#_", 1)[0] for x in data})
# sort languages from highest to lowest average scores
langs_all.sort(key=lambda langs: statistics.mean([
    score
    for line in data if line["doc_id"].startswith(langs + "_#_")
    for score in line["scores_avg"].values()
]))
for ax, langs in zip(axs.flatten(), langs_all):
    data_y = [
        score
        for line in data if line["doc_id"].startswith(langs + "_#_")
        for score in line["scores_avg"].values()
    ]
    data_y_0 = [y for y in data_y if y < 10]
    data_y_1 = [y for y in data_y if y >= 10 and y < 90]
    data_y_2 = [y for y in data_y if y >= 90]
    out = ax.hist(
        data_y,
        bins=10,
        range=(0, 100),
        density=True,
        color="#ccc",
        linewidth=0,
    )
    out[2][0].set_color("#c99")
    out[2][-1].set_color("#9ca")
    ax.set_yticks([])
    lang1, lang2 = langs.split("_")[0].split("-")
    ax.text(
        x=0.5,
        y=1,
        s=f"{lang1}-{lang2}",
        transform=ax.transAxes,
        ha="center",
        va="top",
    )
    if ax in axs[-1, :]:
        ax.set_xlabel("Score", labelpad=-10)
    else:
        ax.set_xticks([])
    if ax in axs[:, 0]:
        ax.set_ylabel("Density")
    ax.spines[["top", "right"]].set_visible(False)

plt.tight_layout(pad=0)
plt.subplots_adjust(hspace=0.1)
plt.savefig("../../generated/humeval_distribution.pdf")
plt.show()

# %%

metrics = [metric for metric in data[0]["metrics"]["Gemini-2.5-Pro"].keys()]

langs_all_0 = [
    "en-ar_EG", "en-bho_IN", "en-sr_Cyrl_RS",
    "en-et_EE", "en-is_IS", "en-ru_RU"
]
langs_all_2 = list({x["doc_id"].split("_#_", 1)[0] for x in data})


def format_cell(acc):
    # if score < 0.25:
    #     color = "Firebrick3!30"
    # else:
    # score = min(1, (score-0.25)/0.75)
    color = f"Firebrick3!{100-acc*100:.0f}!SeaGreen3!{acc*100:.0f}"
    return r"\cellcolor{" + color + "} " + f"{acc:>4.0%}".replace("%", r"\%")


def f1(ys_tpos: set, ys_tneg: set, ys_pred):
    f1s = []
    for threshold_i in range(1, len(ys_pred), 5):
        ys_ppos = {doc_id for y, doc_id in ys_pred[:threshold_i]}
        ys_pneg = {doc_id for y, doc_id in ys_pred[threshold_i:]}

        tp = len(ys_tpos & ys_ppos)
        fp = len(ys_tneg & ys_ppos)
        fn = len(ys_tpos & ys_pneg)
        if tp == 0:
            f1s.append(0)
        else:
            prec = tp / (tp + fp)
            rec = tp / (tp + fn)
            f1s.append(2 * prec * rec / (prec + rec))
    return max(f1s)


with open("../../generated/criticality_prediction_0.tex", "w") as f0:
    print(
        r"\begin{tabular}{l" + "r"*len(langs_all_0) + r"}",
        r"\toprule",
        file=f0,
    )
    print(
        r"\bf Metric",
        *[r"\rotatebox{90}{\bf " +
            langs.split("_")[0] + "}" for langs in langs_all_0],
        sep=" & ",
        end=" \\\\\n",
        file=f0,
    )
    print(r"\midrule", file=f0)
    metrics_out = []
    for metric in tqdm.tqdm(metrics):
        metrics_out_local = []
        for langs in langs_all_0:
            acc_0 = []
            for human_gold, human_metric in [("human1", "human2"), ("human2", "human1")]:
                if metric.startswith("human"):
                    metric = human_metric
                data_yhum = [
                    (sys_v, (line["doc_id"], sys))
                    for line in data if line["doc_id"].startswith(langs + "_#_")
                    for sys, sys_v in line["scores_avg"].items()
                ]
                data_ymet = [
                    (sys_v[metric], (line["doc_id"], sys))
                    for line in data if line["doc_id"].startswith(langs + "_#_")
                    for sys, sys_v in line["metrics"].items()
                ]
                data_yhum_pos = {doc_id for y_hum,
                                 doc_id in data_yhum if y_hum < 10}
                data_yhum_neg = {doc_id for y_hum,
                                 doc_id in data_yhum if y_hum >= 10}

                # take the bottom or top, whichever is better
                data_ymet.sort(key=lambda x: x[0], reverse=False)
                acc_bot = f1(data_yhum_pos, data_yhum_neg, data_ymet)
                data_ymet.sort(key=lambda x: x[0], reverse=True)
                acc_top = f1(data_yhum_pos, data_yhum_neg, data_ymet)
                acc_0.append(max(acc_bot, acc_top))

            metrics_out_local.append(statistics.mean(acc_0))
        metrics_out.append((metric, metrics_out_local))

    for metric, metric_v in sorted(metrics_out, key=lambda x: -statistics.mean(x[1])):
        print(
            f"{metric:>20}".replace('_', r'\_').replace("human1", "Human"),
            file=f0,
        )
        for acc_0 in metric_v:
            print(f" & {format_cell(acc_0)}", end="", file=f0)

        print("\\\\", file=f0)

    print(
        r"\bottomrule",
        r"\end{tabular}",
        file=f0
    )
