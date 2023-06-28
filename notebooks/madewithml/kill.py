from ray.util.scheduling_strategies import NodeAffinitySchedulingStrategy
import requests
import subprocess
import ray
import sys

ray.init()

@ray.remote
def get_instance_id():
    metadata = requests.get(
        "http://instance-data/latest/dynamic/instance-identity/document"
    ).json()
    return subprocess.run(
        [
            "aws",
            "ec2",
            "terminate-instances",
            "--instance-ids",
            metadata["instanceId"],
            "--region",
            metadata["region"],
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


node_id = sys.argv[1]

print(ray.get(get_instance_id.options(scheduling_strategy=NodeAffinitySchedulingStrategy(node_id, soft=False)).remote()))

