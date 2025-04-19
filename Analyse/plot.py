import json
import os
from pathlib import Path

import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd

current_file = Path(__file__).resolve()
data_folder = current_file.parents[0] / 'data'

classify = {
    "BenchMark": ["features-service", "genome-nexus", "languageTool", "market", "person", "emb-project",
                  "restcountries",
                  "user", "ncs", "scs", "news", "catwatch", "proxyprint", "ocvn", "bibliothek", "VAmPI",
                  "session-service",
                  "gestaohospital-rest", "pay-publicapi", "reservations-api", "omdb", "cwa-verfication"],
    "RealWorld": ["gitlab-branch", "gitlab-commit", "gitlab-groups", "gitlab-issues", "gitlab-projects",
                  "gitlab-repository", "Elevations", "Imagery", "Locations", "Route", "TimeZone", "fdic", "spotify",
                  "youtube", "spree", "ohsome", "bitbucket_server", "petstore", "google-drive", "wordpress",
                  "bookstore"]
}

used_structure_info = pd.read_csv(os.path.join(data_folder, "tools", "structure_info.csv")).drop(
    columns=["Unnamed: 0"])
used_data_model_info = pd.read_csv(os.path.join(data_folder, "tools", "data_model_info.csv")).drop(
    columns=["Unnamed: 0"])
used_nlp_info = pd.read_csv(os.path.join(data_folder, "tools", "nlp_info.csv")).drop(
    columns=["Unnamed: 0"])
used_rule_info = pd.read_csv(os.path.join(data_folder, "tools", "obey_info.csv")).drop(
    columns=["Unnamed: 0"])

guru_structure_info = pd.read_csv(os.path.join(data_folder, "guru", "structure_info.csv")).drop(
    columns=["Unnamed: 0"])
guru_data_model_info = pd.read_csv(os.path.join(data_folder, "guru", "data_model_info.csv")).drop(
    columns=["Unnamed: 0"])
guru_nlp_info = pd.read_csv(os.path.join(data_folder, "guru", "nlp_info.csv")).drop(
    columns=["Unnamed: 0"])
guru_rule_info = pd.read_csv(os.path.join(data_folder, "guru", "obey_info.csv")).drop(
    columns=["Unnamed: 0"])

hub_structure_info = pd.read_csv(os.path.join(data_folder, "swaggerhub", "structure_info.csv")).drop(
    columns=["Unnamed: 0"])
hub_data_model_info = pd.read_csv(os.path.join(data_folder, "swaggerhub", "data_model_info.csv")).drop(
    columns=["Unnamed: 0"])
hub_nlp_info = pd.read_csv(os.path.join(data_folder, "swaggerhub", "nlp_info.csv")).drop(
    columns=["Unnamed: 0"])
hub_rule_info = pd.read_csv(os.path.join(data_folder, "swaggerhub", "obey_info.csv")).drop(
    columns=["Unnamed: 0"])

uesd_emb_structure = used_structure_info[used_structure_info['SUT'].isin(classify['BenchMark'])]
uesd_realworld_structure = used_structure_info[used_structure_info['SUT'].isin(classify['RealWorld'])]

uesd_emb_data_model = used_data_model_info[used_data_model_info['SUT'].isin(classify['BenchMark'])]
uesd_realworld_data_model = used_data_model_info[used_data_model_info['SUT'].isin(classify['RealWorld'])]

uesd_emb_nlp = used_nlp_info[used_nlp_info['SUT'].isin(classify['BenchMark'])]
uesd_realworld_nlp = used_nlp_info[used_nlp_info['SUT'].isin(classify['RealWorld'])]

emb_rule_info = used_rule_info[used_rule_info['SUT'].isin(classify['BenchMark'])]
realworld_rule_info = used_rule_info[used_rule_info['SUT'].isin(classify['RealWorld'])]

used_data_model_info["Properties Per Schema"] = used_data_model_info["Properties"] / used_data_model_info[
    "Defined Schemas"]
guru_data_model_info["Properties Per Schema"] = guru_data_model_info["Properties"] / guru_data_model_info[
    "Defined Schemas"]
hub_data_model_info["Properties Per Schema"] = hub_data_model_info["Properties"] / hub_data_model_info[
    "Defined Schemas"]

used_structure_info.drop(index=used_structure_info[used_structure_info.Paths == 0].index, inplace=True)
guru_structure_info.drop(index=guru_structure_info[guru_structure_info.Paths == 0].index, inplace=True)
hub_structure_info.drop(index=hub_structure_info[hub_structure_info.Paths == 0].index, inplace=True)

used_data_model_info.drop(index=used_data_model_info[used_data_model_info["Defined Schemas"] == 0].index, inplace=True)
used_data_model_info.drop(index=used_data_model_info[used_data_model_info["Properties"] == 0].index, inplace=True)
guru_data_model_info.drop(index=guru_data_model_info[guru_data_model_info["Defined Schemas"] == 0].index, inplace=True)
guru_data_model_info.drop(index=guru_data_model_info[guru_data_model_info["Properties"] == 0].index, inplace=True)
hub_data_model_info.drop(index=hub_data_model_info[hub_data_model_info["Defined Schemas"] == 0].index, inplace=True)
hub_data_model_info.drop(index=hub_data_model_info[hub_data_model_info["Properties"] == 0].index, inplace=True)

used_nlp_info.drop(index=used_nlp_info[used_nlp_info["Described Operations"] == 0].index, inplace=True)
used_nlp_info.drop(index=used_nlp_info[used_nlp_info["ARI_Index"] > 100].index, inplace=True)
used_nlp_info.drop(index=used_nlp_info[used_nlp_info["CLI_Index"] > 100].index, inplace=True)
used_nlp_info.drop(index=used_nlp_info[used_nlp_info["Described Operations"] > 100].index, inplace=True)
guru_nlp_info.drop(index=guru_nlp_info[guru_nlp_info["Described Operations"] == 0].index, inplace=True)
guru_nlp_info.drop(index=guru_nlp_info[guru_nlp_info["ARI_Index"] > 100].index, inplace=True)
guru_nlp_info.drop(index=guru_nlp_info[guru_nlp_info["CLI_Index"] > 100].index, inplace=True)
guru_nlp_info.drop(index=guru_nlp_info[guru_nlp_info["Described Operations"] > 100].index, inplace=True)
hub_nlp_info.drop(index=hub_nlp_info[hub_nlp_info["Described Operations"] == 0].index, inplace=True)
hub_nlp_info.drop(index=hub_nlp_info[hub_nlp_info["ARI_Index"] > 100].index, inplace=True)
hub_nlp_info.drop(index=hub_nlp_info[hub_nlp_info["CLI_Index"] > 100].index, inplace=True)
hub_nlp_info.drop(index=hub_nlp_info[hub_nlp_info["Described Operations"] > 100].index, inplace=True)

hub_structure_info.drop(index=hub_structure_info[hub_structure_info["Parameters Per Operations"] > 100].index,
                        inplace=True)
guru_structure_info.drop(index=guru_structure_info[guru_structure_info["Parameters Per Operations"] > 100].index,
                         inplace=True)


def get_rule_rate(info_df):
    rate_df = pd.DataFrame(columns=["SUT", "A1-1%", "A1-2%", "A1-3%", "A1-4%", "A2-1%", "A3-1%", "A4-1%",
                                    "B1-1%", "B1-2%", "B2-1%", "C1-1%", "C1-2%", "C1-3%", "C2-1%", "C2-2%",
                                    "D1-1%", "D1-2%", "D1-3%", "D3-1%", "D3-2%"])
    for row in info_df.iterrows():
        rate_df = rate_df._append({
            "SUT": row[1]["SUT"],
            "A1-1%": row[1]["A1-1"] / row[1]["Paths"] if row[1]["Paths"] != 0 else 0,
            "A1-2%": row[1]["A1-2"] / row[1]["Paths"] if row[1]["Paths"] != 0 else 0,
            "A1-3%": row[1]["A1-3"] / row[1]["Paths"] if row[1]["Paths"] != 0 else 0,
            "A1-4%": row[1]["A1-4"] / row[1]["Paths"] if row[1]["Paths"] != 0 else 0,
            "A2-1%": row[1]["A2-1"] / row[1]["Paths"] if row[1]["Paths"] != 0 else 0,
            "A3-1%": row[1]["A3-1"] / row[1]["Paths"] if row[1]["Paths"] != 0 else 0,
            "A4-1%": row[1]["A4-1"] / row[1]["Operations"] if row[1]["Operations"] != 0 else 0,
            "B1-1%": row[1]["B1-1"] / row[1]["Operations"] if row[1]["Operations"] != 0 else 0,
            "B1-2%": row[1]["B1-2"] / row[1]["Operations with Problem"] if row[1][
                                                                               "Operations with Problem"] != 0 else float(
                'inf'),
            "B2-1%": row[1]["B2-1"] / row[1]["Operations"] if row[1]["Operations"] != 0 else 0,
            "C1-1%": row[1]["C1-1"] / row[1]["Operations"] if row[1]["Operations"] != 0 else 0,
            "C1-2%": row[1]["C1-2"] / row[1]["Operations"] if row[1]["Operations"] != 0 else 0,
            "C1-3%": row[1]["C1-3"] / row[1]["Operations"] if row[1]["Operations"] != 0 else 0,
            "C2-1%": row[1]["C2-1"] / row[1]["Operations"] if row[1]["Operations"] != 0 else 0,
            "C2-2%": row[1]["C2-2"] / row[1]["Operations"] if row[1]["Operations"] != 0 else 0,
            "D1-1%": row[1]["D1-1"] / row[1]["Operations"] if row[1]["Operations"] != 0 else 0,
            "D1-2%": row[1]["D1-2"] / row[1]["Paths"] if row[1]["Paths"] != 0 else 0,
            "D1-3%": row[1]["D1-3"] / row[1]["Operations"] if row[1]["Operations"] != 0 else 0,
            "D3-1%": row[1]["D3-1"] / row[1]["Operations"] if row[1]["Operations"] != 0 else 0,
            "D3-2%": row[1]["D3-2"] / row[1]["Operations"] if row[1]["Operations"] != 0 else 0,
        }, ignore_index=True)
    return rate_df


def count_average_a32(info_df):
    true_count = (info_df['A3-2'] == True).sum()
    false_count = (info_df['A3-2'] == False).sum()
    return true_count / (true_count + false_count)


def count_status(info_df):
    status_count = {}
    for row in info_df.iterrows():
        status = json.loads(row[1]["Status Codes"])
        for code, num in status.items():
            if f"{code[0]}XX" not in status_count:
                status_count[f"{code[0]}XX"] = num
            else:
                status_count[f"{code[0]}XX"] += num
    return status_count


def count_method(info_df):
    method_count = {}
    for row in info_df.iterrows():
        method = json.loads(row[1]["Method Count"])
        for method, num in method.items():
            if method not in method_count:
                method_count[method] = num
            else:
                method_count[method] += num
    return method_count


def count_version(df):
    info = {"Header": 0, "Path": 0, "Query": 0, "Host": 0}
    for row in df.iterrows():
        if row[1]["D1-1"] > 0:
            info["Header"] += 1
        if row[1]["D1-2"] < row[1]["Paths"]:
            info["Path"] += 1
        if row[1]["In Host"]:
            info["Host"] += 1
        if row[1]["D1-3"] > 0:
            info["Query"] += 1
    print(info)
    return info


def plot_pct(dfs, prop):
    raw_infos = []
    infos = []
    if prop == "Status Codes":
        for df in dfs:
            raw_infos.append(count_status(df))
    elif prop == "Method Count":
        for df in dfs:
            raw_infos.append(count_method(df))

    all_keys = set()
    for data in raw_infos:
        all_keys.update(data.keys())

    for data in raw_infos:
        for key in all_keys:
            if key not in data:
                data[key] = 0

    for data in raw_infos:
        new_data = dict(sorted(data.items(), key=lambda x: x[0]))
        infos.append(new_data)

    def concat_data(infos):
        new_data = {}
        for data in infos:
            for key, value in data.items():
                if key not in new_data:
                    new_data[key] = value
                else:
                    new_data[key] += value
        return new_data

    new_infos = []
    new_infos.append(concat_data(infos[:2]))
    new_infos.append(concat_data(infos[2:]))

    def calculate_ratio(data):
        total = sum(data.values())
        to_convert = []
        for key, value in data.items():
            to_convert.append((value / total) * 100)
        return np.array([(value / total) * 100 for value in data.values()])

    ratios1 = calculate_ratio(new_infos[0])
    ratios2 = calculate_ratio(new_infos[1])

    labels = [str(key) for key in sorted(all_keys)]

    label1 = []
    label2 = []
    for i in range(len(labels)):
        if ratios1[i] > 1:
            label1.append(labels[i])
        else:
            label1.append(None)
    for i in range(len(labels)):
        if ratios2[i] > 1:
            label2.append(labels[i])
        else:
            label2.append(None)

    # 创建一个包含两个子图的图形
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))

    # 绘制 Tools 的饼图
    def autopct_format(pct):
        return ('%1.1f%%' % pct) if pct >= 1 else ''

    # 绘制 Tools 的饼图
    axes[0].pie(ratios1, labels=label1, autopct=autopct_format,
                colors=sns.color_palette('Set2'), startangle=90)
    axes[0].set_title("Tools")
    axes[0].axis('equal')

    # 绘制 RealWorld 的饼图
    axes[1].pie(ratios2, labels=label2, autopct=autopct_format,
                colors=sns.color_palette('Set2'), startangle=90)
    axes[1].set_title("RealWorld")
    axes[1].axis('equal')

    fig.suptitle(f'{prop} of OAS by DataSource')
    plt.show()


def boxplot(info_dfs, properties):
    data = {}
    for prop in properties:
        tool_prop = info_dfs[0][prop].to_list() + info_dfs[1][prop].to_list()
        realworld_prop = info_dfs[2][prop].to_list() + info_dfs[3][prop].to_list()
        all_prop = tool_prop + realworld_prop
        save_prop = prop.replace("%", "")
        if "Operations" in prop or "Parameters" in prop:
            save_prop = save_prop.replace("Operations", "Op")
            save_prop = save_prop.replace("Parameters", "Param")
        if "Properties" in prop:
            save_prop = save_prop.replace("Properties", "Prop")
        save_prop = save_prop.replace("Defined", "Def")
        save_prop = save_prop.replace("Distinct", "Dist")
        save_prop = save_prop.replace("Described", "Desc")
        save_prop = save_prop.replace("Property", "Prop")
        data[save_prop] = {}
        data[save_prop]["Tools"] = tool_prop
        data[save_prop]["Realworld"] = realworld_prop
        data[save_prop]["All"] = all_prop

    # 将数据转换为适合 seaborn 的长格式
    data_list = []
    for category, sub_data in data.items():
        for data_type, values in sub_data.items():
            for value in values:
                data_list.append([category, data_type, value])

    df = pd.DataFrame(data_list, columns=["Category", "Data Type", "Value"])

    # 设置图形样式
    sns.set(style="whitegrid")

    # 绘制箱线图
    plt.figure(figsize=(10, 6))
    ax = sns.boxplot(x="Category", y="Value", hue="Data Type", data=df, palette=["#1f77b4", "#ff7f0e", "#2ca02c"],
                     showfliers=False)

    # 设置图例位置
    ax.legend(loc='upper right')

    # 取消图例
    # legend = ax.get_legend()
    # if legend:
    #     legend.remove()

    # 设置图形标题和坐标轴标签
    plt.title("Distribution of documentations of Tools and RealWorld on different specifications")
    plt.xlabel("Data Source")
    plt.ylabel("Value")

    # 显示图形
    plt.show()


def read_data():
    structure_group = [uesd_emb_structure, uesd_realworld_structure, guru_structure_info, hub_structure_info]
    data_model_group = [uesd_emb_data_model, uesd_realworld_data_model, guru_data_model_info, hub_data_model_info]
    nlp_group = [uesd_emb_nlp, uesd_realworld_nlp, guru_nlp_info, hub_nlp_info]
    rule_group = [emb_rule_info, realworld_rule_info, guru_rule_info, hub_rule_info]
    rule_rate_group = [get_rule_rate(rule_info) for rule_info in rule_group]
    return structure_group, data_model_group, nlp_group, rule_group, rule_rate_group


def rq1():
    boxplot(rule_rate_group, ["A1-1%", "A1-2%", "A1-3%", "A1-4%", "A2-1%", "A3-1%", "A4-1%"])
    boxplot(rule_rate_group, ["B1-1%", "B1-2%", "B2-1%"])
    boxplot(rule_rate_group, ["C1-1%", "C1-2%", "C1-3%", "C2-1%", "C2-2%"])

    boxplot(nlp_group, ["Described Operations Rate", "Described Parameters Rate", "Described Property Rate"])
    boxplot(nlp_group, ["CLI_Index"])

    plot_pct(rule_group, "Status Codes")


def rq2():
    boxplot(structure_group, ["Paths", "Methods", "Operations", "Path Depth", "Parameters Per Operations"])
    boxplot(structure_group, ["Used Parameters", "Distinct Parameters", ])
    boxplot(data_model_group,
            ["Defined Schemas", "Distinct Used Schemas", "Properties", "Used Properties", "Distinct Used Properties",
             "Properties Per Schema"])
    plot_pct(structure_group, "Method Count")


if __name__ == '__main__':
    structure_group, data_model_group, nlp_group, rule_group, rule_rate_group = read_data()
    rq1()
    rq2()
