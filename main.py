import itertools
from collections import Counter
import networkx as nx
from tqdm import tqdm
from networkx.algorithms import bipartite
import networkx.algorithms.isomorphism as iso
import math
from multiprocessing import Pool, cpu_count
from functools import partial
import pickle
import gc,os,shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent  # Set current directory as working directory.


def lazy_split(lst, chunk_size):
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i+chunk_size]

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

def hyper_to_graph_filewriter(task):
    i, n_vertices, n_edges = task
    with open(f'{BASE_DIR}/data/hypergraphs/chunk_{i}.pkl', 'rb') as f:
        loaded_chunk = pickle.load(f)
    incident_graphs = []
    for edges, degrees in loaded_chunk:
        # Convert into incident graphs.
        g = hyper_to_graph(n_vertices, n_edges, edges)
        incident_graphs.append(g)
    with open(f"{BASE_DIR}/data/incident/incident_chunk_{i}.pkl", 'wb') as f:
        pickle.dump(incident_graphs, f)  # Save into .pkl files


# Generate all candidate hypergraphs and Convert into incident graphs.
def generate_hypergraphs(n_vertices, n_edges, uniform, n_min_degree, n_workers=None):
    # n_vertices = 6
    # n_edges = 6
    # uniform = 3
    # n_min_degree = 2
    vertices = list(range(n_vertices))
    all_edges = list(itertools.combinations(vertices, uniform))
    hypergraphs = []
    chunk_counter = 0

    pbar = tqdm(total=math.comb(math.comb(n_vertices,uniform),n_edges), desc="Generating hypergraphs", bar_format="{l_bar}{bar:40}{r_bar}{rate_fmt}")

    # Backtrack algorithm
    def backtrack(start, current_edges, degrees):
        if len(current_edges) == n_edges:
            pbar.update(1)  # Update whenever a hypergraph with n edges is generated.
            deg_counts = Counter(degrees)
            if min(degrees) >=n_min_degree:# Minimum degree condition. You can add other conditions there.
                if len(hypergraphs) < 2500000:
                    normalized_edges = tuple(sorted(tuple(sorted(e)) for e in current_edges))
                    hypergraphs.append((normalized_edges, degrees[:]))
                else:
                    nonlocal chunk_counter
                    for idx, chunk in enumerate(lazy_split(hypergraphs, 10000)):
                        filename = f"{BASE_DIR}/data/hypergraphs/chunk_{chunk_counter + idx}.pkl"
                        with open(filename, 'wb') as f:
                            pickle.dump(chunk, f)  # Save into .pkl files
                    hypergraphs.clear()
                    chunk_counter = chunk_counter + idx + 1
                    normalized_edges = tuple(sorted(tuple(sorted(e)) for e in current_edges))
                    hypergraphs.append((normalized_edges, degrees[:]))

            return

        for i in range(start, len(all_edges)):
            edge = all_edges[i]
            new_degrees = degrees.copy()
            valid = True
            for v in edge:
                new_degrees[v] += 1
                if new_degrees[v] > n_edges:
                    valid = False
                    break
            if valid:
                current_edges.append(edge)
                backtrack(i + 1, current_edges, new_degrees)
                current_edges.pop()

    if os.path.exists(f"{BASE_DIR}/data/hypergraphs/"):
        shutil.rmtree(f"{BASE_DIR}/data/hypergraphs/")  # Initial directory
        os.makedirs(f"{BASE_DIR}/data/hypergraphs/")
    else:
        os.makedirs(f"{BASE_DIR}/data/hypergraphs/")
    backtrack(0, [], [0] * n_vertices)
    pbar.close()

    if not hypergraphs: # Save the remaining hypergraphs (fewer than 2.5 million) to .pkl files.
        return chunk_counter
    else:
        for idx, chunk in enumerate(lazy_split(hypergraphs, 10000)):
            filename = f"{BASE_DIR}/data/hypergraphs/chunk_{chunk_counter + idx}.pkl"
            with open(filename, 'wb') as f:
                pickle.dump(chunk, f)  # Save into .pkl files
        del hypergraphs, all_edges
        gc.collect()
        chunk_counter = chunk_counter + idx + 1

    if os.path.exists(f"{BASE_DIR}/data/incident/"):
        shutil.rmtree(f"{BASE_DIR}/data/incident/")  # Initial directory
        os.makedirs(f"{BASE_DIR}/data/incident/")
    else:
        os.makedirs(f"{BASE_DIR}/data/incident/")

    tasks = []
    if n_workers is None:
        n_workers = max(1, cpu_count() - 1)
    for j in range(chunk_counter):
        tasks.append((j, n_vertices, n_edges))
    # Convert into incident graphs.
    with Pool(processes=n_workers) as pool:
        results = list(tqdm(
            pool.imap_unordered(hyper_to_graph_filewriter, tasks),
            total=len(tasks),
            desc="Converting into incident graphs",
            bar_format="{l_bar}{bar:40}{r_bar}{rate_fmt}"
        ))
    '''
    pbar = tqdm(total=len(range(chunk_counter)), desc="Converting into incident graphs.", bar_format="{l_bar}{bar:40}{r_bar}{rate_fmt}")
    # unique_hypergraphs = []
    # seen_incident_graphs = []
    for j in range(chunk_counter):
        # Convert into incident graphs.
        hyper_to_graph_filewriter(j,n_vertices, n_edges)
        pbar.update(1)
            # unique_hypergraphs.append((edges, degrees))
    pbar.close()
    '''


    return chunk_counter

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
def is_berge_k4_saturated(g):
    original_nodes = [n for n, attr in g.nodes(data=True) if attr['bipartite'] == 0]
    hyperedge_nodes = [n for n in g.nodes() if n not in original_nodes]
    n_vertices = len(original_nodes)
    uniform = len(list(g.neighbors(hyperedge_nodes[0])))
    n_edges = len(hyperedge_nodes)
    if is_berge_k4_free(g):
        flag = True
        # Step 1: Calculate the neighborhood of the vertices in original_nodes in the original hypergraph.

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
                union.update((a, b))
            # Check if the size of the set is equal to the uniform and if a set of size equal to the uniform is a hyperedge.
            if len(union) == uniform and tuple(sorted(union)) not in original_edges:
                flag = False
                break
        return (g,flag)
    else:
        return (g,False)

# Do it parallely.
def select_berge_k4_saturated_parallel(incident_graphs, n_workers=None):
    if n_workers is None:
        n_workers = max(1, cpu_count() - 1)

    with Pool(processes=n_workers) as pool:
        results = list(tqdm(
            pool.imap_unordered(is_berge_k4_saturated, incident_graphs),
            total=len(incident_graphs),
            desc="Selecting Berge K_4 saturated",
            bar_format="{l_bar}{bar:40}{r_bar}{rate_fmt}"
        ))

    return [g for g, is_free in results if is_free]

# Check and select non-isomorphic hypergraphs.
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

# Convert incident graphs back to hypergraphs.
def graph_to_hyper(bipartite_graph):
    # Separate the original nodes and the hyperedge nodes.
    original_nodes = {n for n, data in bipartite_graph.nodes(data=True) if data.get('bipartite') == 0}
    hyperedge_nodes = [n for n in bipartite_graph.nodes() if n not in original_nodes]

    # Reconstructing the hyperedge set and initializing the degree sequence.
    degrees = [0] * len(original_nodes)
    hyperedges = []
    for he_node in hyperedge_nodes:
        # Get all original nodes connected to the current hyperedge node.
        connected_nodes = list(bipartite_graph.neighbors(he_node))
        # Ensure that only the original node is included (avoiding hyperedge nodes).
        valid_edges = [n for n in connected_nodes if n in original_nodes]
        hyperedges.append(tuple(sorted(valid_edges)))  # Sort the hyperedges.
        for v in valid_edges:
            degrees[v] += 1

    # Deduplication and filtering of empty hyperedges.
    hyperedges = list(sorted(he for he in set(hyperedges) if len(he) > 0))
    degree_list = [degrees[node] for node in original_nodes]
    return tuple((hyperedges, degree_list))

def main(n_vertices, n_edges, uniform, n_min_degree):
    # Generate all candidate hypergraphs and Convert into incident graphs.
    num_chunks = generate_hypergraphs(n_vertices, n_edges, uniform, n_min_degree)
    list_of_merged_lists = []
    # print(num_chunks)
    for index, index_chunk in enumerate(lazy_split(list(range(num_chunks)), 500)):
        idx = len(index_chunk)
        chunks = [None] * (idx)
        for i in range(idx):
            with open(f"{BASE_DIR}/data/incident/incident_chunk_{i}.pkl", 'rb') as f:
                incident_graphs = pickle.load(f)
            print("Chunk:", index, "/", len(list(lazy_split(list(range(num_chunks)), 500))) - 1, "- Fragment:", i, "/",
                  len(chunks) - 1, "Start")
            # Obtain Berge K4 saturated hypergraphs.
            incident_graphs = select_berge_k4_saturated_parallel(incident_graphs)
            chunks[i] = non_isomorphic(incident_graphs)  # Select non-isomorphic ones.
        merged_list = list(itertools.chain.from_iterable(chunks))
        list_of_merged_lists.append(non_isomorphic(merged_list))
    merged_list = list(itertools.chain.from_iterable(list_of_merged_lists))
    merged_list = non_isomorphic(merged_list)
    # Write merged_list into .pkl file.
    if os.path.exists(f"{BASE_DIR}/data/results/"):
        shutil.rmtree(f"{BASE_DIR}/data/results/")  # Initialization.
        os.makedirs(f"{BASE_DIR}/data/results/")
    else:
        os.makedirs(f"{BASE_DIR}/data/results/")
    with open(f"{BASE_DIR}/data/results/merged_list.pkl", 'wb') as f:
        pickle.dump(merged_list, f)

    hypergraphs = []
    for graph in merged_list:
        hypergraph = graph_to_hyper(graph)
        hypergraphs.append(hypergraph)

    for i, (edges, degrees) in enumerate(hypergraphs, 1):
        print(f"\nHypergraph {i}:")
        print(f"Hyperedges：{edges}")
        print(f"Degree sequence: {degrees}")
    print(f"Found {len(hypergraphs)} non-isomorphic Berge_K4_saturated hypergraphs.")

if __name__ == "__main__":
    main(8,5,3,2)