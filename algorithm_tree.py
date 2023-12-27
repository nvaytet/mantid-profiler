# Mantid algorithm profiler
# Copyright (C) 2018 Neil Vaytet & Igor Gudich, European Spallation Source
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


import copy
import re


class Node:
    def __init__(self, info=[]):
        self.parent = None
        self.level = 0
        self.children = []
        self.info = info

    def to_list(self):
        res = []

        def to_list_int(node, lst):
            lst.append(node)
            for nd in node.children:
                to_list_int(nd, lst)

        to_list_int(self, res)
        return res

    def append(self, tree):
        tree.parent = self
        tree.level = self.level + 1
        self.children.append(tree)

    def find_all(self, cond):
        def find_all_int(node, cond, res):
            if cond(node.info):
                res.append(node)
            for nd in node.children:
                find_all_int(nd, cond, res)

        result = []
        find_all_int(self, cond, result)
        return result

    def find_in_depth(self, cond):
        def find_in_depth_int(node, cond, res):
            if cond(node.info):
                res[0] = node
                for nd in node.children:
                    find_in_depth_int(nd, cond, res)

        result = [None]
        find_in_depth_int(self, cond, result)
        return result[0]

    def find_first(self, cond):
        def find_first_int(node, cond, res):
            if res:
                return
            else:
                if cond(node.info):
                    res.append(node)
                    return
                for nd in node.children:
                    find_first_int(nd, cond, res)

        result = []
        find_first_int(self, cond, result)
        return result[0]

    def clone(self):
        def clone_int(nd_new, nd_old):
            for ch in nd_old.children:
                nd_new.append(Node(copy.deepcopy(ch.info)))
            for i in range(len(nd_old.children)):
                clone_int(nd_new.children[i], nd_old.children[i])

        root = Node(copy.deepcopy(self.info))
        clone_int(root, self)
        return root

    def apply(self, func):
        def apply_int(nd, func):
            nd.info = func(nd.info)
            for ch in nd.children:
                apply_int(ch, func)

        root = self.clone()
        apply_int(root, func)
        return root

    def apply_pairwise(self, other, check, func):
        root = self.clone()
        lst1 = root.to_list()
        lst2 = other.to_list()
        for i in range(len(lst1)):
            if not check(lst1[i].info, lst2[i].info):
                raise RuntimeError("Check failed for pairwise tree operation.")
            lst1[i].info = func(lst1[i].info, lst2[i].info)
        return root

    def apply_from_head_childs(self, func):
        def apply_from_head_childs_int(nd, func):
            nd.info = func(nd.info, [ch.info for ch in nd.children])
            for ch in nd.children:
                apply_from_head_childs_int(ch, func)

        root = self.clone()
        apply_from_head_childs_int(root, func)
        return root


def apply_multiple_trees(trees, check, func):
    root = trees[0].clone()
    lst = root.to_list()
    lists = [x.to_list() for x in trees]
    for i in range(len(lst)):
        if not check([x[i].info for x in lists]):
            raise RuntimeError("Check failed for bulk trees operation.")
        lst[i].info = func([x[i].info for x in lists])
    return root


def parseLine(line):
    res = re.search("ThreadID=([0-9]*), AlgorithmName=(.*), StartTime=([0-9]*), EndTime=([0-9]*)", line)
    return {"thread_id": res.group(1), "name": res.group(2), "start": int(res.group(3)), "finish": int(res.group(4))}


def fromFile(fileName):
    res = []
    header = ""
    with open(fileName) as inp:
        for line in inp:
            if "START_POINT:" in line:
                header = line.strip("\n")
                continue
            res.append(parseLine(line))
    return header, res


def cmp_to_key(mycmp):
    "Convert a cmp= function into a key= function"

    class K:
        def __init__(self, obj, *args):  # noqa: ARG002
            self.obj = obj

        def __lt__(self, other):
            return mycmp(self.obj, other.obj) < 0

        def __gt__(self, other):
            return mycmp(self.obj, other.obj) > 0

        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0

        def __le__(self, other):
            return mycmp(self.obj, other.obj) <= 0

        def __ge__(self, other):
            return mycmp(self.obj, other.obj) >= 0

        def __ne__(self, other):
            return mycmp(self.obj, other.obj) != 0

    return K


def toTrees(records):
    recs = sorted(
        records,
        key=cmp_to_key(lambda x, y: x["start"] - y["start"] if x["start"] != y["start"] else y["finish"] - x["finish"]),
    )

    def rec_to_node(r, counter):
        return Node([r["name"] + " " + str(counter), r["start"], r["finish"], counter])

    heads = []
    counter = dict()
    for rec in recs:
        head = None
        for hd in heads:
            if rec["start"] >= hd.info[1] and rec["finish"] <= hd.info[2]:
                head = hd
                break
        if rec["name"] in counter.keys():
            counter[rec["name"]] += 1
        else:
            counter[rec["name"]] = 1
        if head is None:
            heads.append(rec_to_node(rec, counter[rec["name"]]))
        else:
            parent = head.find_in_depth(cond=lambda x: x[1] <= rec["start"] and rec["finish"] <= x[2])
            parent.append(rec_to_node(rec, counter[rec["name"]]))
        # counter += 1
    return heads
