# Finch Drawing Simulator

A simple Finch "simulator" that shows what the Finch would draw with a pen inserted.

Create a Jupyter notebook and `from finchdraw import Finch` instead of the real Finch library.
To see where your finch has moved, either call `.show()` on your finch instance,
or put the finch instance as the last value in a notebook cell.

See `example.ipynb` for some demonstrations.

## Installation

1. [Install uv](https://docs.astral.sh/uv/getting-started/installation/),
   if you do not already have it.
2. Clone this repository locally
3. In the cloned repository, run `uv sync` to create a virtual environment with the necessary libraries.
    * This will create a `.venv` folder in the project directory.
4. Open the folder in VS Code.
5. Open the `example.ipynb` notebook.
6. In the notebook, click on "Select Kernel", choose "Python Environments…", and then choose "finchdraw" (".venv/bin/python").
