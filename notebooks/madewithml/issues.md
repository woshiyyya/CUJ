# CUJ Issues from Yunxuan

My training settings:
 
- 2 x `g4dn.4xlarge` nodes
- Model: `bert-large-cased`, `AutoModelForSequenceClassification`
- Framework: Use Transformer Trainer with AIR `TorchTrainer`
- Data Ingestion: HF datasets 
- Experiment Tracking: `wandb`
- Storage: `/mnt/cluster_storage`


- Cluster environment: `default_cluster_env_ml_2.5.1_py39:1`

# Environment setup
Time: 10 min

I was using anyscale ray-ml docker, which already contains most of the required libraries. 

I maunally installed HF evaluate library.

Notes:
- Using ray-ml docker might not be a real user experience. Users might start from an empty env and install packages one-by-one.


# Data Preprocessing
Time: 20 min

I choose to use HF datasets for preprocessing, which could be the first choice for OSS ML users. It won't take me much time if you are familiar with HF's APIs.

## Compare HF datasets and Ray Datasets

| | HF Datasets | Ray Data |
| - | - | - |
| Batch format | HF Dataset Batch | Pandas/Numpy |
| Cache | Stores previously downloaded and processed datasets with local PyArrow files | In object store |
| Batch Mapping | `.map(batch=True/False)` | `.map_batches()` |
| Data Loading | `load_dataset(streaming=)` Can either create Map-style Dataset or IterableDataset | Iterable by default |


HF dataset is well integrated with the HF ecosystem:
- HF Datasets: directly load opensource dataset
- HF Datasets: easy batch processing
- HF Evaluate: load evaluation metrics from HF Dataset
- HF Transformers: load evaluation metrics + HF Datasets into Trainer

Question:

Our current logic for TransformerTrainer is:
- convert HF dataset to Ray dataset: `ray.data.from_huggingface()` 
- preprocess in ray style: `ray_ds.map_batches()`
- Convert Ray DataIterator to HF dataset: `TransformersTrainer.process_dataset_for_hf()`

We are converting it back and force: HF Dataset -> Ray Dataset -> HF IterableDataset.

Ray Data should perform some benchmarking to demonstrate at what scale it would have performance benefits over HF Datasets. Below that scale, we recommend using HF Datasets instead.

# Model Definition and configuration
Time: 15min

It only took me 1min to define a bert-large-cased model, since `from_pretrained()` has configured everything for me. The only annoying thing is to define a `AIRReportCallback` by myself. It collects metrics and calls `session.report` internally. This should not be a burden for users after we make `ray.train.huggingface.transformers.AIRReportCallback` public.


# Model Training
Time: ~1h

Debugging training code takes a lot of time. The major obstacle is that I did many operations on the head node and use them as global variable in the `train_loop_per_worker`.

- Data
  - HF Dataset cannot find cache file on worker node
- Wandb
  - environment variable won't be copied the worker node
- Evaluate
  - import error when you load evaluate metrics outside of training loop

# Issues
## 1. `evaluate` library import error

```
TuneError                                 Traceback (most recent call last)
TuneError: Failure # 1 (occurred at 2023-07-17_11-32-18)
The actor died because of an error raised in its creation task, ray::_Inner.__init__() (pid=74105, ip=10.0.59.208, actor_id=1587da442278a7fcb939991101000000, repr=TorchTrainer)
  File "/home/ray/anaconda3/lib/python3.9/site-packages/ray/tune/trainable/trainable.py", line 170, in __init__
    self.setup(copy.deepcopy(self.config))
  File "/home/ray/anaconda3/lib/python3.9/site-packages/ray/tune/trainable/util.py", line 305, in setup
    setup_kwargs[k] = parameter_registry.get(prefix + k)
  File "/home/ray/anaconda3/lib/python3.9/site-packages/ray/tune/registry.py", line 301, in get
    return ray.get(self.references[k])
ray.exceptions.RaySystemError: System error: No module named 'evaluate_modules'
traceback: Traceback (most recent call last):
ModuleNotFoundError: No module named 'evaluate_modules'
```

Found an GH Issue: https://github.com/huggingface/transformers/issues/22408, but seems that we haven't resolve this yet. It turns out that this happens not only  when using ray in Transformer, also when using Transformer in ray.

Under the hood, `evaluate.load` will download scripts for the evaluation metric into local cache dir, which is not accessible from remote worker. 

**Solution:** Moving `accuracy = evaluate.load("accuracy")` into `train_loop_per_worker`

**Action:** We need to make sure sure if the transformers integration works now.


## 2. Huge core dump file in the working directory

```
(base) ray@ip-10-0-59-208:~/yx-dev/notebooks/madewithml$ ls -lha
total 627M
drwxr-xr-x 2 ray users 4.0K Jul 17 11:40 .
drwxr-xr-x 3 ray users 4.0K Jul 17 10:52 ..
-rw------- 1 ray users 778M Jul 17 11:40 core.68866 <- This one
-rw-r--r-- 1 ray users 1.1K Jul 17 11:40 issues.md
-rw-r--r-- 1 ray users  774 Jul 17 10:52 kill.py
-rw-r--r-- 1 ray users 265K Jul 17 11:40 madewithml.ipynb
```

Ray will set up the runtime env by packaging all the files in the current working directory and sending them to the remote node. Huge core dumps cause this failure:

```
RuntimeEnvSetupError: Failed to set up runtime environment.
Failed to upload package /tmp/ray_latest_runtime_env.zip to the Ray cluster: Package size (777.48MiB) exceeds the maximum size of 500.00MiB. You can exclude large files using the 'excludes' option to the runtime_env or provide a remote URI of a zip file using protocols such as 's3://', 'https://' and so on, refer to https://docs.ray.io/en/latest/ray-core/handling-dependencies.html#api-reference.
```

**Workaround:** Maunally delete the dump files. 

**Action:** This file should not be placed in the current working directory. Discuss with Core team and move this out of CWD?


## 3. HF dataset cache file not found

```
FileNotFoundError: [Errno 2] Failed to open local file '/home/ray/.cache/huggingface/datasets/csv/default-e255c49ad510847c/0.0.0/433e0ccc46f9880962cc2b12065189766fbb2bee57a221866138fb9203c83519/cache-81e96195f77f350f.arrow'. Detail: [errno 2] No such file or directory
```

The problem is that HF datasets by default will load from a cached pyarrow file, and this file is stored under `~/.cache/huggingface/datasets`, which is not accessible for remote workers. 

**Workaround:** I have to add `load_datasets(keep_in_memory=True)`, but this is not applicable when we have a large dataset. 

Related discussions: https://anyscaleteam.slack.com/archives/C03G7N1PE0P/p1689621578398859

**Action:** 
- Put this issue in HF-related documentation (new Train Doc - Transformers - FAQ)
- Better error messages on Ray side?


## 4. Re-definition the Transformer's Trainer after training finished

The normal way to evaluate on a model for HF Transformers is to call `trainer.evaluate()` (similar to PyTorch Lightning).

The users cannot retrieve the Trainer defined in training loop, since `trainer.fit()` does not return any in-memory objects. We have to copy and paste the same code blocks to re-define a Trainer.

**Action:** 
- It's actually not a big problem, because most users will include the evaluation dataset and do evaluation during training.
- Is it possible that we can return customized in-memory objects?


## 5. Need user guides for AIR Storage Design.

To avoid potential issues, it is crucial that I have a 100% clear understanding of Ray AIR's storage design. This is a missing part of our current doc.

- Difference between local path and remote path
- HF libraries often use local caches, so we should recommend to place everything into `train_loop_per_worker` instead of creating global variables on the head node and automatically capture them.


## 6. Environment Variables

I set the `"WANDB_API_KEY"` environment variable on the head node, but it does not exist in the worker loop, causing the process to fail to log in to wandb. 


**Solution:** To fix this, I need to 
- capture the API key on the head node 
- pass it to the worker through `train_loop_config` (or global variable)
- set this env var again in the worker loop

**Action:** Should we explicitly provide a list of environment variables to be captured on the head node and dumped to the workers?
