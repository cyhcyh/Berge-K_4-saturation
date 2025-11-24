import itertools
from collections import Counter
import networkx as nx
from networkx.algorithms import bipartite
import networkx.algorithms.isomorphism as iso
import math


def sort_matching(matching):
    def sort_tuple_and_int(data):
        return tuple(sorted(data, key=lambda x: (1 if isinstance(x, tuple) else 0, x)))

    matching = list(matching)

    for idx in range(len(matching)):
        matching[idx] = sort_tuple_and_int(matching[idx])
    return matching

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
    berge_k4 = []
    cores = None
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
            for he_node, pair in sort_matching(nx.max_weight_matching(aux_g, maxcardinality=True)):
                # Get all original nodes connected to the current hyperedge node.
                connected_nodes = list(g.neighbors(he_node))
                # Ensure that only the original node is included (avoiding hyperedge nodes).
                valid_edges = [n for n in connected_nodes if n in original_nodes]
                berge_k4.append(tuple(sorted(valid_edges)))  # Sort the hyperedges.

                # Deduplication and filtering of empty hyperedges.
            berge_k4 = list(sorted(he for he in set(berge_k4) if len(he) > 0))
            cores = q
            flag = False
            break
    return berge_k4, cores, flag

def is_berge_k4_saturated(n_vertices,hyperedges):
    uniform = len(hyperedges[0])
    n_edges = len(hyperedges)
    g = hyper_to_graph(n_vertices,n_edges,hyperedges)
    berge_k4, cores, is_berge_k4_free_flag = is_berge_k4_free(g)
    if is_berge_k4_free_flag:
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
                bad_edge = union
                flag = False
                break
        if flag and n_vertices >= 5:
            print("It is Berge K_4 saturated!!")
        else:
            if n_vertices < 5:
                print("No, too small to be Berge K_4 saturated!!")
            else:
                print("No, one of bad edges is:", bad_edge)
                print("Bad pairs are:", bad)
    else:
        print("Found Berge K_4:",berge_k4,"\nWith cores:",cores)

    return


if __name__ == "__main__":
    # hyperedges = [(0, 1, 2), (1, 2, 3), (2, 3, 4), (3, 4, 0), (4, 5, 1), (2, 4, 5)]
    hyperedges = [(0, 1, 2), (0, 1, 3), (0, 1, 4), (0, 2, 5), (1, 2, 6), (1, 3, 5), (2, 3, 6)]
    is_berge_k4_saturated(7, hyperedges)