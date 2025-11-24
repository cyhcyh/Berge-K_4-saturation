import itertools
from collections import Counter
import networkx as nx
from networkx.algorithms import bipartite
import networkx.algorithms.isomorphism as iso
import math
from multiprocessing import Pool, cpu_count

from tqdm import tqdm

def check_isomorphic(g, exist):

    return nx.vf2pp_is_isomorphic(g, exist, node_label='bipartite')

def non_isomorphic(incident_graphs, n_workers=None,chunk = 50):
    # pbar = tqdm(total=len(incident_graphs), desc="Selecting non-isomorphic", bar_format="{l_bar}{bar:40}{r_bar}{rate_fmt}")
    # Selecting non-isomorphic by VF2++ algorithm.
    # unique_hypergraphs = []
    noniso_incident_graphs = []
    if n_workers is None:
        n_workers = max(1, cpu_count() - 1)
    with Pool(processes=n_workers) as pool, \
            tqdm(total=len(incident_graphs), desc="Selecting non-isomorphic", bar_format="{l_bar}{bar:40}{r_bar}{rate_fmt}") as pbar:

        for g in incident_graphs:
            if not noniso_incident_graphs:  # Add the first hypergraph.
                noniso_incident_graphs.append(g)
                pbar.update(1)
                continue

            chunks = [noniso_incident_graphs[i:i + chunk] for i in range(0, len(noniso_incident_graphs), chunk)]

            # Asynchronously submit all chunk tasks.
            futures = [pool.apply_async(check_isomorphic, (g, exist))
                       for chunk in chunks for exist in chunk]

            # Check results in real time.
            is_new = True
            for i, future in enumerate(futures):
                if future.get():
                    is_new = False
                    # Abort subsequent checks.
                    for f in futures[i + 1:]:
                        f.wait()
                    break

            if is_new:
                noniso_incident_graphs.append(g)
            pbar.update(1)
    pbar.close()

    return list(noniso_incident_graphs)

# Convert hypergraphs into auxiliary bipartite graphs (incident_graphs).
def hyper_to_graph(n_vertices,n_edges,hyperedges):
    aux_g = nx.Graph()
    hyper_nodes = [n_vertices + i for i in range(n_edges)]
    aux_g.add_nodes_from(list(range(n_vertices)), bipartite=0)
    aux_g.add_nodes_from(hyper_nodes, bipartite=1)
    for i, edge in enumerate(hyperedges):
        hyperedge_vertex = n_vertices + i
        for v in edge:
            aux_g.add_edge(v, hyperedge_vertex)
    return aux_g

# Determine Berge K_4 freeness
def is_berge_k4_free(g):
    flag = True
    original_nodes = {n for n, data in g.nodes(data=True) if data.get('bipartite') == 0}
    hyperedge_nodes = [n for n in g.nodes() if n not in original_nodes]
    quartets = list(itertools.combinations(original_nodes, 4))
    for q in quartets:
        aux_g = nx.Graph()
        left_nodes = list(itertools.combinations(sorted(q), 2))
        aux_g.add_nodes_from(left_nodes, bipartite=0)
        aux_g.add_nodes_from(hyperedge_nodes, bipartite=1)
        for pair in left_nodes:
            v1, v2 = pair
            # Find the hyperedge_nodes that is connected to both v1 and v2.
            common_hyperedges = set(g.neighbors(v1)) & set(g.neighbors(v2))
            for he in common_hyperedges:
                if he in hyperedge_nodes:  # Make sure it is a hyperedge_node
                    aux_g.add_edge(pair, he)
        if len(nx.max_weight_matching(aux_g, maxcardinality=True)) == len(left_nodes):
            flag = False
            break
    return flag

# Determine if a hypergraph is Berge K_4 saturated.
def is_berge_k4_saturated(n_vertices,hyperedges):
    uniform = len(hyperedges[0])
    n_edges = len(hyperedges)
    g = hyper_to_graph(n_vertices,n_edges,hyperedges)
    if is_berge_k4_free(g):
        flag = True
        bad_edge = []
        # Step 1: Calculate the neighborhood of the vertices in original_nodes in the original hypergraph.
        original_nodes = [n for n, attr in g.nodes(data=True) if attr['bipartite'] == 0]
        hyperedge_nodes = [n for n in g.nodes() if n not in original_nodes]
        original_edges = []
        for e in hyperedge_nodes:
            original_edges.append(tuple(sorted(g.neighbors(e))))
        neighbor_dict = {}
        for v in original_nodes:
            hyperedges = list(g.neighbors(v))
            neighbors = set()
            for he in hyperedges:
                neighbors.update(g.neighbors(he))
            neighbors.discard(v)
            neighbor_dict[v] = neighbors

        # Step 2: Find all pairs with elements in original_nodes.
        all_pairs = list(itertools.combinations(original_nodes, 2))

        # Step 3: Find all bad pairs.
        bad = []

        for u, v in all_pairs:
            # Calculate common neighbors and filter by degree condition.
            common = neighbor_dict[u].intersection(neighbor_dict[v])
            filtered = [w for w in common if g.degree(w) >= 3]

            if len(filtered) < 2:
                bad.append((u, v))
                continue

            # Consider all pairs of the rest common neighbors and verify whether (u,v) is good.
            satisfied = False
            for w, x in itertools.combinations(filtered, 2):
                quad = (u, v, w, x)
                aux_g = nx.Graph()
                left_nodes = list(itertools.combinations(sorted(quad), 2))
                left_nodes.remove((u, v))
                aux_g.add_nodes_from(left_nodes, bipartite=0)
                aux_g.add_nodes_from(hyperedge_nodes, bipartite=1)
                for pair in left_nodes:
                    v1, v2 = pair
                    # Find the hyperedge_nodes that is connected to both v1 and v2.
                    common_hyperedges = set(g.neighbors(v1)) & set(g.neighbors(v2))
                    for he in common_hyperedges:
                        if he in hyperedge_nodes:  # Make sure it is a hyperedge_node.
                            aux_g.add_edge(pair, he)
                if len(nx.max_weight_matching(aux_g, maxcardinality=True)) == len(left_nodes):
                    satisfied = True
                    break

            if not satisfied:
                bad.append((u, v))
        # Determine if there are 3 bad pairs form a non-hyperedge.
        for trio in itertools.combinations(bad, math.comb(uniform, 2)):
            # Remove duplicates by putting elements into a set.
            union = set()
            for a, b in trio:
                union.update((a, b))  # 自动去重
            # Check if the size of the set is equal to the uniform and if a set of size equal to the uniform is a hyperedge.
            if len(union) == uniform and tuple(sorted(union)) not in original_edges:
                # bad_edge = union
                flag = False
                break
        return flag
    else:
        return False

def check_one_pair(task):
    n_vertices, hyperedges, pair = task
    u, v = pair
    hyperedges.append((u,n_vertices,n_vertices + 1))
    hyperedges.append((v, n_vertices, n_vertices + 1))
    n_vertices += 2
    g = hyper_to_graph(n_vertices, len(hyperedges), hyperedges)
    return (pair, g, is_berge_k4_saturated(n_vertices,hyperedges))

def can_induction(n_vertices, hyperedges, n_workers=None):
    all_pairs = list(itertools.combinations(list(range(n_vertices)), 2))
    tasks = []
    if n_workers is None:
        n_workers = max(1, cpu_count() - 1)
    for pair in all_pairs:
        tasks.append((n_vertices, hyperedges, pair))

    with Pool(processes=n_workers) as pool:
        results = list(tqdm(
            pool.imap_unordered(check_one_pair, tasks),
            total=len(tasks),
            desc="Checking...",
            bar_format="{l_bar}{bar:40}{r_bar}{rate_fmt}"
        ))
    incident_graphs = [g for pair, g, flag in results if flag]
    incident_graphs = non_isomorphic(incident_graphs)

    final = [pair for pair, g, flag in results if g in incident_graphs]
    if len(final):
        print("Can add on ",sorted(final),".")
    else:
        print("Cannot add.")

    return


if __name__ == "__main__":
    hyperedges = [(0, 1, 2), (0, 1, 3), (0, 2, 4), (1, 3, 4), (2, 3, 4)]
    # hyperedges = [(0, 1, 2), (0, 1, 3), (0, 1, 4), (0, 2, 5), (0, 2, 6), (1, 3, 5), (4, 5, 6)]
    can_induction(5, hyperedges)