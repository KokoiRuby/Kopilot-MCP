from kubernetes import client, config  # type: ignore
from kubernetes.dynamic import DynamicClient  # type: ignore
from kubernetes.client import ApiClient  # type: ignore
from config.config import config as conf


__all__ = ("create_dynamic_client", )


kubernetes_config = conf["kubernetes"]


async def create_dynamic_client() -> DynamicClient:
    return DynamicClient(ApiClient(
        configuration=config.load_kube_config(
            config_file=kubernetes_config["kubeconfig"]),
    ))
