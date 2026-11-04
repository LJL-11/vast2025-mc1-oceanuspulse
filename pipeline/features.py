from __future__ import annotations

import argparse
import bisect
import json
import math
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.stats import mannwhitneyu
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "MC1_graph.json"
OUT = ROOT / "data" / "processed" / "rising_star.json"

SNAPSHOT_YEAR = 2040
HORIZON = 5
SAILOR_ID = 17255
SEED = 2025

ROLE_TYPES = {"PerformerOf", "ComposerOf", "LyricistOf", "ProducerOf"}
INFLUENCE_TYPES = {
    "InStyleOf",
    "InterpolatesFrom",
    "CoverOf",
    "DirectlySamples",
    "LyricalReferenceTo",
}
FOLK_GENRES = {
    "Oceanus Folk",
    "Sea Shanties",
    "Celtic Folk",
    "Acoustic Folk",
    "Indie Folk",
    "Post-Apocalyptic Folk",
    "Avant-Garde Folk",
    "Americana",
}
PRESTIGE_LABELS = {"Coastal Harmony Studios", "Oceanic Records"}

FEATURES = [
    ("career_age", "职业年龄", "快照年份减去出道年份"),
    ("log_works", "作品数(log)", "截至快照年份的作品数量"),
    ("notable_rate", "上榜作品占比", "notable=True 的作品比例"),
    ("single_share", "单曲占比", "single=True 的作品比例"),
    ("active_recent", "近3年活跃", "快照前 3 年是否有新作"),
    ("last_gap", "距上次发片年数", "快照年份减去最近作品年份"),
    ("momentum", "产出动量", "近 3 年作品数 / 前 3 年作品数"),
    ("gap_cv", "发片间隔变异系数", "作品年份间隔的标准差 / 均值"),
    ("log_collab", "合作者数(log)", "去重后的合作人数"),
    ("collab_per_work", "每作品合作者数", "合作人数 / 作品数"),
    ("star_collab_rate", "高影响力合作者占比", "合作者中拥有 >=5 部上榜作品者比例"),
    ("top_star_collab", "顶级合作者数(log)", "拥有 >=20 部上榜作品的合作者数"),
    ("log_influence_in", "被引用影响力(log)", "其他作品指向其作品的风格/采样/翻唱边数"),
    ("influence_in_rate", "每作品被引用数", "被引用边数 / 作品数"),
    ("log_influence_out", "引用他人影响力(log)", "其作品指向其他作品的边数"),
    ("genre_diversity", "流派多样性", "作品流派的 Shannon 熵"),
    ("oceanus_share", "Oceanus Folk 占比", "Oceanus Folk 作品比例"),
    ("folk_share", "民谣家族占比", "民谣相关流派作品比例"),
    ("log_groups", "所属团体数(log)", "成员所属 MusicalGroup 数量"),
    ("label_prestige", "SS 关联厂牌占比", "Oceanic Records / Coastal Harmony Studios 发行作品比例"),
    ("sailor_works", "Sailor Shift 合作作品(log)", "与 Sailor Shift 共同署名的作品数"),
    ("recent_works_3y", "近 3 年作品数", "快照前 3 年内的新作数量"),
    ("n_sailor_works", "Sailor Shift 合作作品数", "与 Sailor Shift 共同署名的作品数（原始值）"),
    ("n_top_star_works", "顶级艺人合作作品数", "与至少一位 >=20 部上榜作品的艺人共同署名的作品数"),
    ("n_members", "团体规模", "该艺人/组合的成员数量"),
]
MODEL_FEATURES = [
    "sailor_works",
    "recent_works_3y",
    "log_works",
    "log_groups",
    "genre_diversity",
    "notable_rate",
    "star_collab_rate",
]
FEATURE_KEYS = MODEL_FEATURES
UNIVARIATE_FEATURES = list(
    dict.fromkeys(
        MODEL_FEATURES
        + [
            "career_age",
            "momentum",
            "last_gap",
            "log_collab",
            "log_influence_in",
            "log_influence_out",
            "label_prestige",
            "oceanus_share",
            "folk_share",
            "top_star_collab",
        ]
    )
)
COMPOSITE_WEIGHTS = {
    "mentor": 0.30,
    "momentum": 0.25,
    "quality": 0.15,
    "collaboration": 0.10,
    "influence": 0.10,
    "prestige": 0.10,
}


def year_of(value):
    if value is None:
        return None
    text = str(value).strip()
    if len(text) < 4 or not text[:4].isdigit():
        return None
    year = int(text[:4])
    return year if 1900 <= year <= 2100 else None


def shannon_entropy(values):
    total = sum(values.values())
    if total <= 0:
        return 0.0
    entropy = 0.0
    for count in values.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log(p)
    return entropy


def fdr_bh(pvalues):
    pvalues = np.asarray(pvalues, dtype=float)
    n = len(pvalues)
    order = np.argsort(pvalues)
    adjusted = np.empty(n, dtype=float)
    previous = 1.0
    for rank in range(n - 1, -1, -1):
        index = order[rank]
        value = min(previous, pvalues[index] * n / (rank + 1))
        adjusted[index] = value
        previous = value
    return adjusted


class GraphContext:
    def __init__(self, nodes, links):
        self.nodes = {node["id"]: node for node in nodes}
        self.links = links
        self.type = {node_id: node.get("Node Type") for node_id, node in self.nodes.items()}
        self.work_ids = {i for i, t in self.type.items() if t in ("Song", "Album")}
        self.person_ids = {i for i, t in self.type.items() if t == "Person"}
        self.group_ids = {i for i, t in self.type.items() if t == "MusicalGroup"}
        self.label_ids = {i for i, t in self.type.items() if t == "RecordLabel"}

        self.work_year = {}
        self.work_notable = {}
        self.work_hit_year = {}
        self.work_genre = {}
        self.work_single = {}
        for wid in self.work_ids:
            node = self.nodes[wid]
            self.work_year[wid] = year_of(node.get("release_date")) or year_of(node.get("written_date"))
            self.work_notable[wid] = bool(node.get("notable"))
            self.work_hit_year[wid] = year_of(node.get("notoriety_date"))
            self.work_genre[wid] = node.get("genre")
            self.work_single[wid] = bool(node.get("single"))

        self.group_members = defaultdict(set)
        self.person_groups = defaultdict(set)
        for edge in links:
            if edge.get("Edge Type") != "MemberOf":
                continue
            source, target = edge["source"], edge["target"]
            if source in self.person_ids and target in self.group_ids:
                self.group_members[target].add(source)
                self.person_groups[source].add(target)

        self.work_persons = defaultdict(set)
        self.person_direct_works = defaultdict(set)
        self.group_works = defaultdict(set)
        self.work_label = {}
        self.person_credit = defaultdict(int)
        for edge in links:
            edge_type = edge.get("Edge Type")
            source, target = edge["source"], edge["target"]
            if edge_type in ROLE_TYPES and target in self.work_ids:
                if source in self.person_ids:
                    self.work_persons[target].add(source)
                    self.person_direct_works[source].add(target)
                    self.person_credit[source] += 1
                elif source in self.group_ids:
                    members = self.group_members.get(source, set())
                    self.work_persons[target] |= members
                    self.group_works[source].add(target)
                    for member in members:
                        self.person_credit[member] += 1
            elif edge_type in ("RecordedBy", "DistributedBy"):
                if source in self.work_ids and target in self.label_ids:
                    self.work_label[source] = self.nodes[target].get("name")
                elif source in self.label_ids and target in self.work_ids:
                    self.work_label[target] = self.nodes[source].get("name")

        self.person_works = defaultdict(set)
        for person_id in self.person_ids:
            self.person_works[person_id] |= self.person_direct_works.get(person_id, set())
            for group_id in self.person_groups.get(person_id, ()):
                self.person_works[person_id] |= self.group_works.get(group_id, set())

        self.person_notable_years = {}
        for person_id, works in self.person_works.items():
            years = sorted(
                self.work_year[wid]
                for wid in works
                if self.work_notable.get(wid) and self.work_year.get(wid) is not None
            )
            self.person_notable_years[person_id] = years

        self.work_in = defaultdict(list)
        self.work_out = defaultdict(list)
        for edge in links:
            if edge.get("Edge Type") not in INFLUENCE_TYPES:
                continue
            source, target = edge["source"], edge["target"]
            if source in self.work_ids and target in self.work_ids:
                self.work_in[target].append((source, self.work_year.get(source)))
                self.work_out[source].append((target, self.work_year.get(target)))

        self.acts = self._build_acts()
        self.person_to_act = {}
        for act in self.acts:
            for member in act["members"]:
                self.person_to_act[member] = act["act_id"]
        self.act_by_id = {act["act_id"]: act for act in self.acts}

    def notable_count_at(self, person_id, cutoff):
        years = self.person_notable_years.get(person_id, [])
        return bisect.bisect_right(years, cutoff)

    def _build_acts(self):
        active = {pid for pid in self.person_ids if self.person_works.get(pid)}
        parent = {pid: pid for pid in active}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        signatures = defaultdict(list)
        for person_id in active:
            signatures[frozenset(self.person_works[person_id])].append(person_id)
        for members in signatures.values():
            if len(members) >= 2 and len(self.person_works[members[0]]) >= 2:
                for member in members[1:]:
                    union(members[0], member)

        for members in self.group_members.values():
            members = [member for member in members if member in active]
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    a, b = members[i], members[j]
                    works_a = self.person_works[a]
                    works_b = self.person_works[b]
                    union_size = len(works_a | works_b)
                    if union_size and len(works_a & works_b) / union_size >= 0.8:
                        union(a, b)

        components = defaultdict(list)
        for person_id in active:
            components[find(person_id)].append(person_id)

        acts = []
        for members in components.values():
            works = set()
            for person_id in members:
                works |= self.person_works[person_id]
            years = [self.work_year[wid] for wid in works if self.work_year.get(wid) is not None]
            if not years:
                continue

            representative = max(
                members,
                key=lambda pid: (self.person_credit.get(pid, 0), -pid),
            )

            group_scores = Counter()
            for person_id in members:
                for group_id in self.person_groups.get(person_id, ()):
                    group_scores[group_id] += len(self.group_works.get(group_id, set()) & works)
            group_id = None
            if group_scores:
                candidate_group, _ = group_scores.most_common(1)[0]
                group_works = self.group_works.get(candidate_group, set()) & works
                if (
                    self.group_members.get(candidate_group, set()).issubset(set(members))
                    and len(group_works) >= 0.6 * len(works)
                ):
                    group_id = candidate_group

            if group_id is not None:
                name = self.nodes[group_id].get("name")
            else:
                representative_node = self.nodes[representative]
                name = representative_node.get("stage_name") or representative_node.get("name")

            member_list = sorted(members)
            member_names = []
            for member in member_list:
                member_node = self.nodes[member]
                member_names.append(member_node.get("stage_name") or member_node.get("name"))

            genres = Counter(self.work_genre[wid] for wid in works if self.work_genre.get(wid))
            hit_years = sorted(
                self.work_hit_year[wid]
                for wid in works
                if self.work_hit_year.get(wid) is not None
            )

            acts.append(
                {
                    "act_id": min(members),
                    "name": name,
                    "group_id": group_id,
                    "members": member_list,
                    "member_names": member_names,
                    "representative": representative,
                    "representative_name": self.nodes[representative].get("stage_name")
                    or self.nodes[representative].get("name"),
                    "works": works,
                    "debut": min(years),
                    "last_active": max(years),
                    "n_works": len(works),
                    "genres": genres,
                    "oceanus_share_final": genres.get("Oceanus Folk", 0) / max(1, len(works)),
                    "folk_share_final": sum(genres.get(g, 0) for g in FOLK_GENRES) / max(1, len(works)),
                    "hit_years": hit_years,
                }
            )
        acts.sort(key=lambda act: act["act_id"])
        return acts

    def act_features(self, act, cutoff):
        works = [
            wid
            for wid in act["works"]
            if self.work_year.get(wid) is not None and self.work_year[wid] <= cutoff
        ]
        if not works:
            return None

        n_works = len(works)
        years = [self.work_year[wid] for wid in works]
        genres = Counter(self.work_genre[wid] for wid in works if self.work_genre.get(wid))
        oceanus_share = genres.get("Oceanus Folk", 0) / n_works
        folk_share = sum(genres.get(genre, 0) for genre in FOLK_GENRES) / n_works
        notable = sum(1 for wid in works if self.work_notable.get(wid))
        singles = sum(1 for wid in works if self.work_single.get(wid))
        hits_prior = sum(
            1
            for wid in works
            if self.work_hit_year.get(wid) is not None and self.work_hit_year[wid] <= cutoff
        )

        recent = sum(1 for year in years if cutoff - 2 <= year <= cutoff)
        previous = sum(1 for year in years if cutoff - 5 <= year <= cutoff - 3)
        momentum = (recent + 1) / (previous + 1)
        last_gap = cutoff - max(years)

        unique_years = sorted(set(years))
        if len(unique_years) >= 2:
            gaps = [b - a for a, b in zip(unique_years, unique_years[1:])]
            gap_mean = sum(gaps) / len(gaps)
            gap_cv = (sum((g - gap_mean) ** 2 for g in gaps) / len(gaps)) ** 0.5 / gap_mean if gap_mean else 0.0
        else:
            gap_cv = 0.0

        own_members = set(act["members"])
        collaborators = set()
        for wid in works:
            collaborators |= self.work_persons.get(wid, set())
        collaborators -= own_members
        n_collab = len(collaborators)
        star_collab = sum(1 for pid in collaborators if self.notable_count_at(pid, cutoff) >= 5)
        top_star_collab = sum(1 for pid in collaborators if self.notable_count_at(pid, cutoff) >= 20)

        own_works = set(works)
        influence_in = 0
        for wid in works:
            for source_work, source_year in self.work_in.get(wid, ()):
                if source_work in own_works:
                    continue
                if source_year is not None and source_year <= cutoff:
                    influence_in += 1
        influence_out = 0
        for wid in works:
            for target_work, target_year in self.work_out.get(wid, ()):
                if target_work in own_works:
                    continue
                if target_year is not None and target_year <= cutoff:
                    influence_out += 1

        sailor_works = 0
        top_star_works = 0
        for wid in works:
            credited = self.work_persons.get(wid, set()) - own_members
            if SAILOR_ID in credited:
                sailor_works += 1
            if any(self.notable_count_at(pid, cutoff) >= 20 for pid in credited):
                top_star_works += 1

        groups = set()
        for member in act["members"]:
            groups |= self.person_groups.get(member, set())

        prestige_works = sum(1 for wid in works if self.work_label.get(wid) in PRESTIGE_LABELS)

        features = {
            "career_age": cutoff - act["debut"],
            "log_works": math.log1p(n_works),
            "notable_rate": notable / n_works,
            "single_share": singles / n_works,
            "active_recent": 1.0 if recent > 0 else 0.0,
            "last_gap": last_gap,
            "momentum": momentum,
            "gap_cv": gap_cv,
            "log_collab": math.log1p(n_collab),
            "collab_per_work": n_collab / n_works,
            "star_collab_rate": star_collab / n_collab if n_collab else 0.0,
            "top_star_collab": math.log1p(top_star_collab),
            "log_influence_in": math.log1p(influence_in),
            "influence_in_rate": influence_in / n_works,
            "log_influence_out": math.log1p(influence_out),
            "genre_diversity": shannon_entropy(genres),
            "oceanus_share": oceanus_share,
            "folk_share": folk_share,
            "log_groups": math.log1p(len(groups)),
            "label_prestige": prestige_works / n_works,
            "sailor_works": math.log1p(sailor_works),
            "recent_works_3y": float(recent),
            "n_sailor_works": sailor_works,
            "n_top_star_works": top_star_works,
            "n_members": len(act["members"]),
            "log_members": math.log1p(len(act["members"])),
        }
        features.update(
            {
                "n_works": n_works,
                "n_songs": sum(1 for wid in works if self.type.get(wid) == "Song"),
                "n_albums": sum(1 for wid in works if self.type.get(wid) == "Album"),
                "n_notable": notable,
                "n_hits_prior": hits_prior,
                "n_hits_window": None,
                "n_collaborators": n_collab,
                "n_star_collaborators": star_collab,
                "n_top_star_collaborators": top_star_collab,
                "n_collaboration_works": sum(1 for wid in works if len(self.work_persons.get(wid, set()) - own_members) > 0),
                "influence_in": influence_in,
                "influence_out": influence_out,
                "sailor_collab": 1 if SAILOR_ID in collaborators else 0,
                "last_active": max(years),
                "active_years": sorted(set(years)),
            }
        )
        return features

    def timeline(self, act, start=None, end=None):
        start = act["debut"] if start is None else start
        end = SNAPSHOT_YEAR if end is None else end
        rows = []
        cumulative_works = cumulative_notable = cumulative_hits = 0
        for year in range(start, end + 1):
            works = [
                wid
                for wid in act["works"]
                if self.work_year.get(wid) == year
            ]
            n_works = len(works)
            n_notable = sum(1 for wid in works if self.work_notable.get(wid))
            n_hits = sum(1 for wid in works if self.work_hit_year.get(wid) == year)
            cumulative_works += n_works
            cumulative_notable += n_notable
            cumulative_hits += n_hits
            rows.append(
                {
                    "year": year,
                    "works": n_works,
                    "notable": n_notable,
                    "hits": n_hits,
                    "cumulative_works": cumulative_works,
                    "cumulative_notable": cumulative_notable,
                    "cumulative_hits": cumulative_hits,
                }
            )
        return rows

    def shared_works_with(self, act, person_id, cutoff=SNAPSHOT_YEAR):
        return sorted(
            wid
            for wid in act["works"]
            if person_id in self.work_persons.get(wid, set())
            and self.work_year.get(wid) is not None
            and self.work_year[wid] <= cutoff
        )

    def evidence(self, act, cutoff=SNAPSHOT_YEAR):
        evidence = []
        if SAILOR_ID in act["members"]:
            evidence.append("Sailor Shift 本人（本研究的参照巨星）")
        else:
            sailor_works = self.shared_works_with(act, SAILOR_ID, cutoff)
            if sailor_works:
                titles = " / ".join(
                    self.nodes[wid].get("name", str(wid)) for wid in sailor_works[:4]
                )
                evidence.append(
                    f"与 Sailor Shift 共同署名 {len(sailor_works)} 部作品：{titles}"
                )
        labels = Counter(
            self.work_label[wid]
            for wid in act["works"]
            if self.work_year.get(wid) is not None
            and self.work_year[wid] <= cutoff
            and self.work_label.get(wid)
        )
        if labels:
            label, count = labels.most_common(1)[0]
            evidence.append(f"主要发行厂牌：{label}（{count} 部作品）")
        if act["group_id"] is not None:
            evidence.append(f"团体：{self.nodes[act['group_id']].get('name')}")
        if act["member_names"]:
            evidence.append("成员：" + "、".join(act["member_names"]))
        recent = sorted(
            [
                self.nodes[wid].get("name")
                for wid in act["works"]
                if self.work_year.get(wid) is not None
                and self.work_year[wid] >= max(act["debut"], cutoff - 3)
            ]
        )
        if recent:
            evidence.append(f"近 3 年作品 {len(recent)} 部：{' / '.join(recent[:5])}")
        if act["hit_years"]:
            evidence.append(f"历史登榜年份：{', '.join(str(y) for y in act['hit_years'])}")
        else:
            evidence.append("截至 2040 年尚无登榜记录")
        return evidence


def load_graph(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["nodes"], data["links"]


def training_rows(context):
    rows = []
    for act in context.acts:
        if act["n_works"] < 2:
            continue
        for offset in range(0, 8):
            cutoff = act["debut"] + offset
            if cutoff > SNAPSHOT_YEAR - HORIZON:
                break
            features = context.act_features(act, cutoff)
            if features is None or features["n_hits_prior"] > 0:
                continue
            label = 1 if any(cutoff < year <= cutoff + HORIZON for year in act["hit_years"]) else 0
            rows.append(
                {
                    "act_id": act["act_id"],
                    "cutoff": cutoff,
                    "features": features,
                    "label": label,
                }
            )
    return rows


def rows_to_matrix(rows):
    X = np.array(
        [[row["features"][key] for key in FEATURE_KEYS] for row in rows],
        dtype=float,
    )
    y = np.array([row["label"] for row in rows], dtype=int)
    groups = np.array([row["act_id"] for row in rows], dtype=int)
    return X, y, groups


def make_model():
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(
            class_weight="balanced",
            max_iter=5000,
            C=1.0,
            random_state=SEED,
        ),
    )


def cross_validate(X, y, groups):
    cv = GroupKFold(n_splits=5)
    predictions = np.zeros(len(y), dtype=float)
    for train_index, test_index in cv.split(X, y, groups):
        model = make_model()
        model.fit(X[train_index], y[train_index])
        predictions[test_index] = model.predict_proba(X[test_index])[:, 1]
    return {
        "auc": float(roc_auc_score(y, predictions)),
        "average_precision": float(average_precision_score(y, predictions)),
        "brier": float(brier_score_loss(y, predictions)),
        "n_samples": int(len(y)),
        "n_acts": int(len(set(groups.tolist()))),
        "positive_rate": float(y.mean()),
    }


def snapshot_for_univariate(rows):
    by_act = defaultdict(list)
    for row in rows:
        by_act[row["act_id"]].append(row)
    selected = []
    for act_rows in by_act.values():
        preferred = [row for row in act_rows if row["cutoff"] == row["features"]["career_age"] + 2]
        selected.append(preferred[0] if preferred else act_rows[0])
    return selected


def univariate_tests(rows):
    selected = snapshot_for_univariate(rows)
    positives = [row for row in selected if row["label"] == 1]
    negatives = [row for row in selected if row["label"] == 0]
    results = []
    for key in UNIVARIATE_FEATURES:
        positive_values = np.array([row["features"][key] for row in positives], dtype=float)
        negative_values = np.array([row["features"][key] for row in negatives], dtype=float)
        if len(positive_values) == 0 or len(negative_values) == 0:
            continue
        statistic, pvalue = mannwhitneyu(positive_values, negative_values, alternative="two-sided")
        results.append(
            {
                "feature": key,
                "median_positive": float(np.median(positive_values)),
                "median_negative": float(np.median(negative_values)),
                "mean_positive": float(np.mean(positive_values)),
                "mean_negative": float(np.mean(negative_values)),
                "p_value": float(pvalue),
                "statistic": float(statistic),
            }
        )
    adjusted = fdr_bh([item["p_value"] for item in results])
    for item, qvalue in zip(results, adjusted):
        item["p_fdr"] = float(qvalue)
    return {
        "n_positive": len(positives),
        "n_negative": len(negatives),
        "tests": sorted(results, key=lambda item: item["p_value"]),
    }


def candidate_pool(context):
    pool = []
    for act in context.acts:
        features = context.act_features(act, SNAPSHOT_YEAR)
        if features is None:
            continue
        if act["debut"] < 2028 or act["last_active"] < 2035:
            continue
        if features["n_hits_prior"] > 0:
            continue
        if features["oceanus_share"] < 0.5 or features["n_works"] < 2:
            continue
        pool.append((act, features))
    if len(pool) >= 3:
        return pool, "strict"
    relaxed = []
    for act in context.acts:
        features = context.act_features(act, SNAPSHOT_YEAR)
        if features is None:
            continue
        if act["debut"] < 2028 or act["last_active"] < 2033:
            continue
        if features["n_hits_prior"] > 0:
            continue
        if features["folk_share"] < 0.5 or features["n_works"] < 2:
            continue
        relaxed.append((act, features))
    return relaxed, "relaxed"


def bootstrap_scores(rows, candidate_matrix, n_bootstrap=200):
    by_act = defaultdict(list)
    for index, row in enumerate(rows):
        by_act[row["act_id"]].append(index)
    act_ids = list(by_act)
    X, y, _ = rows_to_matrix(rows)
    scores = []
    rng = np.random.default_rng(SEED)
    for _ in range(n_bootstrap):
        sampled_acts = rng.choice(act_ids, size=len(act_ids), replace=True)
        indices = []
        for act_id in sampled_acts:
            indices.extend(by_act[act_id])
        X_sample = X[indices]
        y_sample = y[indices]
        if len(set(y_sample.tolist())) < 2:
            continue
        model = make_model()
        model.fit(X_sample, y_sample)
        scores.append(model.predict_proba(candidate_matrix)[:, 1])
    if not scores:
        return None
    return np.array(scores, dtype=float)


def model_coefficients(model):
    scaler = model.named_steps["standardscaler"]
    classifier = model.named_steps["logisticregression"]
    coefficients = classifier.coef_[0]
    results = []
    for key, coefficient in zip(FEATURE_KEYS, coefficients):
        results.append(
            {
                "feature": key,
                "coefficient": float(coefficient),
                "odds_ratio": float(math.exp(coefficient)),
                "abs_coefficient": float(abs(coefficient)),
                "scaler_mean": float(scaler.mean_[FEATURE_KEYS.index(key)]),
            }
        )
    return sorted(results, key=lambda item: item["abs_coefficient"], reverse=True)


def drivers_for(model, features):
    scaler = model.named_steps["standardscaler"]
    classifier = model.named_steps["logisticregression"]
    values = np.array([[features[key] for key in FEATURE_KEYS]], dtype=float)
    standardized = scaler.transform(values)[0]
    contributions = standardized * classifier.coef_[0]
    results = []
    for key, contribution in zip(FEATURE_KEYS, contributions):
        results.append(
            {
                "feature": key,
                "contribution": float(contribution),
                "value": float(features[key]),
            }
        )
    results.sort(key=lambda item: abs(item["contribution"]), reverse=True)
    return results


def composite_strengths(features):
    return {
        "mentor": 3.0 * features["n_sailor_works"]
        + 1.5 * features["n_top_star_works"]
        + features["star_collab_rate"],
        "momentum": features["recent_works_3y"]
        + 0.5 * features["active_recent"]
        + 1.0 / (1.0 + features["last_gap"])
        + 0.1 * features["momentum"],
        "quality": features["notable_rate"],
        "collaboration": math.log1p(
            features["n_collaborators"] + features["n_members"]
        ),
        "influence": features["log_influence_in"]
        + features["log_influence_out"]
        + features["influence_in_rate"],
        "prestige": features["label_prestige"],
    }


def percentile_rank(value, sorted_values):
    if not sorted_values:
        return 0.0
    left = bisect.bisect_left(sorted_values, value)
    right = bisect.bisect_right(sorted_values, value)
    return (left + right) / 2.0 / len(sorted_values) * 100.0


def composite_reference(context):
    records = []
    for act in context.acts:
        if act["debut"] < 2028 or act["last_active"] < 2030:
            continue
        if act["folk_share_final"] < 0.3:
            continue
        features = context.act_features(act, SNAPSHOT_YEAR)
        if features is None:
            continue
        records.append((act, features))
    strengths = [composite_strengths(features) for _, features in records]
    sorted_values = {
        key: sorted(item[key] for item in strengths) for key in COMPOSITE_WEIGHTS
    }
    return records, sorted_values


def composite_for(features, sorted_values):
    strengths = composite_strengths(features)
    percentiles = {
        key: percentile_rank(strengths[key], sorted_values[key])
        for key in COMPOSITE_WEIGHTS
    }
    score = sum(
        COMPOSITE_WEIGHTS[key] * percentiles[key] for key in COMPOSITE_WEIGHTS
    )
    return float(score), percentiles, strengths


def act_summary(context, act, features, sorted_values=None):
    summary = {
        "act_id": act["act_id"],
        "name": act["name"],
        "group_id": act["group_id"],
        "representative": act["representative"],
        "representative_name": act["representative_name"],
        "members": act["members"],
        "member_names": act["member_names"],
        "debut": act["debut"],
        "last_active": act["last_active"],
        "n_works": act["n_works"],
        "primary_genre": act["genres"].most_common(1)[0][0] if act["genres"] else None,
        "genre_counts": dict(act["genres"].most_common(6)),
        "oceanus_share": float(features["oceanus_share"]),
        "folk_share": float(features["folk_share"]),
        "n_hits": int(features["n_hits_prior"]),
        "features": {key: float(features[key]) for key in FEATURE_KEYS},
        "descriptive": {
            key: float(features[key])
            for key in (
                "n_sailor_works",
                "n_top_star_works",
                "recent_works_3y",
                "n_members",
                "n_collaborators",
                "influence_in",
                "influence_out",
                "label_prestige",
                "notable_rate",
                "momentum",
                "last_gap",
                "career_age",
            )
        },
        "timeline": context.timeline(act),
        "evidence": context.evidence(act),
    }
    if sorted_values is not None:
        score, percentiles, strengths = composite_for(features, sorted_values)
        summary["rising_star_score"] = round(score, 2)
        summary["strength_percentiles"] = {
            key: round(value, 2) for key, value in percentiles.items()
        }
        summary["strengths"] = {
            key: round(value, 4) for key, value in strengths.items()
        }
    return summary


def select_comparison(context, sorted_values=None):
    targets = [
        (17255, "已成名：全球巨星", "慢热型：2024 年出道，2028 年单曲爆红，此后持续高产"),
        (17340, "爆发型新星", "爆发型：2029 年集中发行 8 部作品，7 部同年登榜"),
        (17041, "渐进型候选", "渐进型：2034-2038 年持续输出，截至 2040 尚未登榜"),
    ]
    selected = []
    for person_id, role, note in targets:
        act_id = context.person_to_act.get(person_id)
        act = context.act_by_id.get(act_id) if act_id is not None else None
        if act is None:
            continue
        features = context.act_features(act, SNAPSHOT_YEAR)
        if features is None:
            continue
        summary = act_summary(context, act, features, sorted_values)
        summary["role"] = role
        summary["note"] = note
        selected.append(summary)
    return selected


def build_output(context, rows, model, cv_result, univariate, pool, pool_mode, bootstrap, coefficients):
    reference_records, sorted_values = composite_reference(context)
    X_candidates = np.array(
        [[features[key] for key in FEATURE_KEYS] for _, features in pool],
        dtype=float,
    )
    model_probabilities = (
        model.predict_proba(X_candidates)[:, 1] if len(pool) else np.array([])
    )

    candidate_index = {
        act["act_id"]: index for index, (act, _) in enumerate(pool)
    }
    composite = {}
    for act, features in pool:
        score, percentiles, strengths = composite_for(features, sorted_values)
        composite[act["act_id"]] = (score, percentiles, strengths)

    ordered = sorted(
        zip(pool, model_probabilities),
        key=lambda item: (composite[item[0][0]["act_id"]][0], item[1]),
        reverse=True,
    )

    bootstrap_rank1 = {}
    bootstrap_mean = {}
    if bootstrap is not None and bootstrap.size:
        best = np.argmax(bootstrap, axis=1)
        for act, _ in pool:
            index = candidate_index[act["act_id"]]
            if index >= bootstrap.shape[1]:
                continue
            bootstrap_rank1[act["act_id"]] = float(np.mean(best == index))
            bootstrap_mean[act["act_id"]] = float(np.mean(bootstrap[:, index]))

    predictions = []
    for rank, ((act, features), model_probability) in enumerate(ordered, start=1):
        score, percentiles, strengths = composite[act["act_id"]]
        predictions.append(
            {
                "rank": rank,
                "act_id": act["act_id"],
                "name": act["name"],
                "group_id": act["group_id"],
                "members": act["members"],
                "member_names": act["member_names"],
                "representative": act["representative"],
                "representative_name": act["representative_name"],
                "debut": act["debut"],
                "last_active": act["last_active"],
                "score": round(score, 2),
                "model_probability": float(model_probability),
                "bootstrap_model_probability_mean": bootstrap_mean.get(act["act_id"]),
                "bootstrap_rank1_share": bootstrap_rank1.get(act["act_id"]),
                "features": {key: float(features[key]) for key in FEATURE_KEYS},
                "strength_percentiles": {
                    key: round(value, 2) for key, value in percentiles.items()
                },
                "strengths": {
                    key: round(value, 4) for key, value in strengths.items()
                },
                "raw": {
                    "n_works": features["n_works"],
                    "n_songs": features["n_songs"],
                    "n_albums": features["n_albums"],
                    "n_notable": features["n_notable"],
                    "n_collaborators": features["n_collaborators"],
                    "n_star_collaborators": features["n_star_collaborators"],
                    "n_top_star_collaborators": features["n_top_star_collaborators"],
                    "n_sailor_works": features["n_sailor_works"],
                    "n_top_star_works": features["n_top_star_works"],
                    "recent_works_3y": features["recent_works_3y"],
                    "influence_in": features["influence_in"],
                    "influence_out": features["influence_out"],
                    "sailor_collab": features["sailor_collab"],
                },
                "top_drivers": drivers_for(model, features)[:6],
                "timeline": context.timeline(act),
                "evidence": context.evidence(act),
            }
        )

    leaderboard = []
    for act in context.acts:
        if act["debut"] < 2028 or act["last_active"] < 2033:
            continue
        features = context.act_features(act, SNAPSHOT_YEAR)
        if features is None or features["oceanus_share"] < 0.3:
            continue
        score, percentiles, _ = composite_for(features, sorted_values)
        leaderboard.append(
            {
                "act_id": act["act_id"],
                "name": act["name"],
                "group_id": act["group_id"],
                "primary_genre": act["genres"].most_common(1)[0][0] if act["genres"] else None,
                "debut": act["debut"],
                "last_active": act["last_active"],
                "n_works": act["n_works"],
                "n_members": len(act["members"]),
                "had_hit": bool(features["n_hits_prior"] > 0),
                "oceanus_share": float(features["oceanus_share"]),
                "folk_share": float(features["folk_share"]),
                "score": round(score, 2),
                "model_probability": float(
                    model.predict_proba(
                        np.array([[features[key] for key in FEATURE_KEYS]], dtype=float)
                    )[0, 1]
                ),
            }
        )
    leaderboard.sort(key=lambda item: item["score"], reverse=True)

    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "raw_graph": "data/raw/MC1_graph.json",
            "snapshot_year": SNAPSHOT_YEAR,
            "prediction_window": [SNAPSHOT_YEAR, SNAPSHOT_YEAR + HORIZON],
            "n_nodes": len(context.nodes),
            "n_edges": len(context.links),
            "n_acts": len(context.acts),
            "n_training_samples": len(rows),
            "positive_rate": float(np.mean([row["label"] for row in rows])),
            "candidate_pool": pool_mode,
            "reference_acts": len(reference_records),
            "model_features": list(FEATURE_KEYS),
            "composite_weights": dict(COMPOSITE_WEIGHTS),
            "sailor_id": SAILOR_ID,
        },
        "features": [
            {"key": key, "label": label, "description": description}
            for key, label, description in FEATURES
        ],
        "comparison": select_comparison(context, sorted_values),
        "predictions": predictions,
        "candidates": [
            act_summary(context, act, features, sorted_values)
            for act, features in pool
        ],
        "leaderboard": leaderboard[:80],
        "validation": {
            "cross_validation": cv_result,
            "univariate": univariate,
            "coefficients": coefficients,
            "composite_weights": dict(COMPOSITE_WEIGHTS),
        },
    }


def main():
    global SEED
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(OUT))
    parser.add_argument("--bootstrap", type=int, default=200)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    SEED = args.seed
    random.seed(SEED)
    np.random.seed(SEED)

    nodes, links = load_graph(RAW)
    context = GraphContext(nodes, links)
    rows = training_rows(context)
    X, y, groups = rows_to_matrix(rows)

    cv_result = cross_validate(X, y, groups)
    model = make_model()
    model.fit(X, y)
    coefficients = model_coefficients(model)
    univariate = univariate_tests(rows)

    pool, pool_mode = candidate_pool(context)
    candidate_matrix = np.array(
        [[features[key] for key in FEATURE_KEYS] for _, features in pool],
        dtype=float,
    )
    bootstrap = None
    if pool and args.bootstrap > 0:
        bootstrap = bootstrap_scores(rows, candidate_matrix, n_bootstrap=args.bootstrap)

    output = build_output(
        context,
        rows,
        model,
        cv_result,
        univariate,
        pool,
        pool_mode,
        bootstrap,
        coefficients,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, default=float),
        encoding="utf-8",
    )

    print(f"acts={len(context.acts)} training={len(rows)} positives={int(y.sum())}")
    print(f"cv_auc={cv_result['auc']:.4f} ap={cv_result['average_precision']:.4f} brier={cv_result['brier']:.4f}")
    print(f"candidate_pool={pool_mode} candidates={len(pool)}")
    for prediction in output["predictions"]:
        share = prediction["bootstrap_rank1_share"]
        share_text = f" rank1_share={share:.2f}" if share is not None else ""
        print(
            f"  #{prediction['rank']} {prediction['name']} "
            f"score={prediction['score']:.2f} "
            f"model_p={prediction['model_probability']:.3f}{share_text}"
        )
    print(f"written: {out_path}")


if __name__ == "__main__":
    main()
