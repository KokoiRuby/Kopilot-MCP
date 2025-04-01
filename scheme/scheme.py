import subprocess
from typing import Dict
from kubernetes.client.models import V1ParamKind  # type: ignore
from dataclasses import dataclass
from config.config import config


__all__ = ("parse_api_resources", )


kubernetes_config = config["kubernetes"]


@dataclass
class Resource:
    gvk: V1ParamKind
    is_namespaced: bool


async def parse_api_resources() -> dict[str, Resource]:
    scheme = {}

    # TODO: I don't find a better way to build the scheme using official Python client library for kubernetes.
    # https://github.com/kubernetes-client/python
    # I tried discovery client, but I only get group/version pairs.
    # If you have a better solution, please let me know:)
    result = subprocess.run(['kubectl', 'api-resources', '--no-headers=true', f'--kubeconfig={kubernetes_config["kubeconfig"]}'],
                            capture_output=True,
                            text=True,
                            check=True)

    for line in result.stdout.splitlines():
        parts = [part for part in line.strip().split() if part]
        name = parts[0].strip()
        api_version = parts[-3].strip()
        kind = parts[-1].strip()
        is_namespaced = parts[-2].strip()
        # TODO: How to deal with duplicate keys? Although it's unlikely to conflict.
        # Such as:
        #   events in api/v1
        #   events in events.k8s.io/v1
        # One way is use tuple (name, shortnames) as key, but it get complex when we use it.
        # Besides, they have the same shortnames, ummmmm.

        # TODO: Need to consider shortnames, or maybe we could leave it to guide llm to generate plural only.
        scheme[name] = Resource(
            gvk=V1ParamKind(api_version=api_version, kind=kind),
            is_namespaced=(is_namespaced == 'true'),
        )

    return scheme
