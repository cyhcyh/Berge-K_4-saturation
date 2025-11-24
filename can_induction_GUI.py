import multiprocessing
import sys
import ast
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QTextEdit,
                             QMessageBox, QGroupBox)
from PyQt5.QtCore import QObject, pyqtSignal


class EmittingStream(QObject):
    textWritten = pyqtSignal(str)

    def write(self, text): self.textWritten.emit(str(text))

    def flush(self): pass


class MultiHypergraphGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        sys.stdout = EmittingStream(textWritten=self.handleOutput)

    def initUI(self):
        self.setWindowTitle('Small structure addition judger')
        self.setMinimumWidth(800)
        main_layout = QVBoxLayout()

        # Input area
        input_group = QGroupBox("Input hypergraphs")
        input_layout = QVBoxLayout()

        # Input the number of vertices
        vertex_layout = QHBoxLayout()
        vertex_layout.addWidget(QLabel("Number of vertices: "))
        self.vertex_input = QLineEdit()
        self.vertex_input.setPlaceholderText("Example: 6")
        vertex_layout.addWidget(self.vertex_input)
        input_layout.addLayout(vertex_layout)

        # Input hypergraphs
        hyper_layout = QVBoxLayout()
        hyper_layout.addWidget(QLabel("Hypergraph list (One hypergraph each line, in Python tuple list format): "))
        self.hyper_input = QTextEdit()
        self.hyper_input.setPlaceholderText("Example: \n[(0, 1, 2), (0, 1, 3), (0, 2, 4), (0, 3, 5), (1, 2, 5), (3, 4, 5)]\n[(0, 1, 2), (0, 1, 3), (0, 4, 5), (1, 4, 5), (2, 3, 4), (2, 3, 5)]")
        hyper_layout.addWidget(self.hyper_input)
        input_layout.addLayout(hyper_layout)

        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)

        # Action button
        self.run_btn = QPushButton("Verify")
        self.run_btn.clicked.connect(self.batch_validate)
        main_layout.addWidget(self.run_btn)

        # Output area
        output_group = QGroupBox("Results")
        output_layout = QVBoxLayout()
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        output_layout.addWidget(self.output_area)
        output_group.setLayout(output_layout)
        main_layout.addWidget(output_group)

        self.setLayout(main_layout)

    def handleOutput(self, text):
        self.output_area.moveCursor(self.output_area.textCursor().End)
        self.output_area.insertPlainText(text)
        self.output_area.ensureCursorVisible()

    def batch_validate(self):
        # Verify the number of vertices
        try:
            n_vertices = int(self.vertex_input.text())
            if n_vertices <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.critical(self, "Input error", "The number of vertices must be a positive integer.")
            return

        # Parse hypergraph list
        hypergraphs = []
        raw_text = self.hyper_input.toPlainText().strip()
        if not raw_text:
            QMessageBox.critical(self, "Input error", "Hypergraph list cannot be empty.")
            return

        for line_num, line in enumerate(raw_text.split('\n'), 1):
            line = line.strip()
            if not line: continue

            try:
                hyperedges = ast.literal_eval(line)
                if not isinstance(hyperedges, list):
                    raise TypeError("It must be in list format.")

                # Format validation
                uniform = None
                valid_edges = []
                for idx, edge in enumerate(hyperedges, 1):
                    if not isinstance(edge, tuple):
                        raise ValueError(f"The item {idx} is not a tuple.")

                    sorted_edge = tuple(sorted(edge))
                    if any(v < 0 or v >= n_vertices for v in sorted_edge):
                        raise ValueError(f"The item {idx} contains invalid vertices.")

                    if uniform is None:
                        uniform = len(sorted_edge)
                    elif len(sorted_edge) != uniform:
                        raise ValueError(f"The length of the item {idx} is inconsistent.")

                    valid_edges.append(sorted_edge)

                hypergraphs.append(valid_edges)

            except Exception as e:
                QMessageBox.critical(
                    self, "Format error",
                    f"Parsing line {line_num} failed：\n{str(e)}\n"
                    "Example of correct format：\n[(0,1,2), (0,1,3)]"
                )
                return

        # Perform batch verification
        self.output_area.clear()
        for idx, hyperedges in enumerate(hypergraphs, 1):
            self.output_area.append(f"▶▶ Analyzing hypergraph {idx} (with {len(hyperedges)} hyperedges): ")
            try:
                from can_induction import can_induction
                can_induction(n_vertices, hyperedges)
            except Exception as e:
                self.output_area.append(f"Run-time Error: {str(e)}")
            self.output_area.append("━" * 60 )


if __name__ == '__main__':
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    window = MultiHypergraphGUI()
    window.show()
    sys.exit(app.exec_())