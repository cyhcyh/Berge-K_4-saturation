import os
import pickle
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent  # 脚本所在目录

def graph_to_hyper(bipartite_graph):
    # 分离原节点与超边辅助节点
    original_nodes = {n for n, data in bipartite_graph.nodes(data=True) if data.get('bipartite') == 0}
    hyperedge_nodes = [n for n in bipartite_graph.nodes() if n not in original_nodes]

    # 重建超边集合以及初始化原图点度
    degrees = [0] * len(original_nodes)
    hyperedges = []
    for he_node in hyperedge_nodes:
        # 获取当前辅助节点连接的所有原节点
        connected_nodes = list(bipartite_graph.neighbors(he_node))
        # 过滤确保只包含原节点（避免连接其他辅助节点）
        valid_edges = [n for n in connected_nodes if n in original_nodes]
        hyperedges.append(tuple(sorted(valid_edges)))  # 排序保证超边有序
        for v in valid_edges:
            degrees[v] += 1

    # 去重并过滤空超边
    hyperedges = list(sorted(he for he in set(hyperedges) if len(he) > 0))
    degree_list = [degrees[node] for node in original_nodes]
    return tuple((hyperedges, degree_list))

if __name__ == "__main__":
    # if os.path.exists(f"{BASE_DIR}/data/results/"):
    #     shutil.rmtree(f"{BASE_DIR}/data/results/")  # 递归删除目录及内容
    #     os.makedirs(f"{BASE_DIR}/data/results/")
    # else:
    #     os.makedirs(f"{BASE_DIR}/data/results/")
    with open(f"{BASE_DIR}/data/results/merged_list.pkl", 'rb') as f:
        merged_list = pickle.load(f)

    hypergraphs = []
    for graph in merged_list :
        hypergraph = graph_to_hyper(graph)
        hypergraphs.append(hypergraph)

    for i, (edges, degrees) in enumerate(hypergraphs, 1):
        # print(f"\nHypergraph {i}:")
        print(f"{edges}")
        # print(f"度序列：{degrees}")
    print(f"Found {len(hypergraphs)} non-isomorphic Berge_K4_saturated hypergraphs.")