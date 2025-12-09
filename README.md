# Berge-K_4-saturation

This repository provides the implementation of the algorithm described in the paper:  
**[TBA]** ([Link](TBA)).

The program is designed to search all uniform Berge K_4 saturated hypergraphs with given number of vertices and hyperedges in parallel.
**It has been optimized and tested to run on a personal computer, but it is recommended to run it on a dedicated server for better performance (which will be faster).**

---

## 📦 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/cyhcyh/Berge-K_4-saturation.git
   cd Berge-K_4-saturation
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   > ✅ **Python 3.12 or higher could be better**.

---

## ▶️ Usage

1. Open `main.py` and locate the `main()` function.
2. Modify the parameters (number of vertices, number of hyperedges, uniform, least vertex degree) according to your needs.
3. Run the program:
   ```bash
   python main.py
   ```

The program will output all uniform Berge K_4 saturated hypergraphs with settled number of vertices and hyperedges.

---

## 🛠️ Supplementary Tools

Two standalone utilities with GUI are provided in **[The calculators with GUI](https://github.com/cyhcyh/Berge-K_4-saturation/releases/tag/1.0)**:

- **`can_induction`**: Check each of the input hypergraphs and decide wether it can add $\mathcal{T}$. If can, print all vertex pairs on which $\mathcal{T}$ can be add on.
- **`is_saturated`**: Check each of the input hypergraphs and decide wether it is Berge-K_4 saturated. If not, print the found Berge-K_4, or print the first non-hyperedge whose addition does not create a new Berge-K_4, and all bad pairs.

The Windows and Linux versions are both provided.

---

## 🔧 Extending

- To comptue Berge-G saturated uniform hypergraphs for arbitrary graph G, please modify the ways to construct the auxiliary graph `aux_g` accordingly.
- The code can be modified to compute non-uniform hypergraphs.

---

## 📚 Citation

If you use this code in your research, please cite our paper:

```bibtex
@article{TBA,
  title={Title},
  author={Authors},
  journal={Journal Name},
  year={2025+},
}
```

---

## 📄 License

This project is licensed under the MIT License – see the [LICENSE](https://github.com/cyhcyh/Berge-K_4-saturation/blob/master/LICENSE) file for details.

---

*Developed with ❤️ for advancing extremal graph theory research.*
