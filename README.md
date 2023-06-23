# Critical User Journeys (CUJ)

## Set up

```bash
# Git clone
git clone https://github.com/anyscale/CUJ.git .
```

```bash
# Environment
export PYTHONPATH=$PYTHONPATH:$PWD
python3 -m venv venv  # recommend using Python 3.10
source venv/bin/activate  # on Windows: venv\Scripts\activate
python3 -m pip install --upgrade pip setuptools wheel
pip install jupyter_contrib_nbextensions
jupyter contrib nbextension install --user
jupyter lab notebooks/madewithml.ipynb
```

> If you're on Anyscale Workspaces (which is highly recommended), you don't need to use a virtual environment.

## CUJs

Each bolded section in the notebook is a distinct CUJ with a few details about it. We'll also include hidden recommendations relevant to the CUJ that you can expand to view. The goal is to complete the CUJs by using [Ray documentation](https://docs.ray.io/en/latest/), our Slack channels (#train-cuj) for support or view parts of the (one possible) solution [here](https://github.com/anyscale/Made-With-ML/blob/main/notebooks/madewithml.ipynb), etc. You may find that some CUJs are very open-ended. Feel free to approach the task however you wish and when we convene for the CUJ, we can compare our approaches.

> When you pip install a package, be sure to do it directly in the notebook (`pip install LIBRARY[VERSION] -q`) so we can see what packages you're using. Alternatively, you can store the information in the `requirements.txt` file. You will want to do `pip install --user LIBRARY[VERSION] -q` when working inside Anyscale Workspaces so that all the worker nodes can also have access to the version of the library.