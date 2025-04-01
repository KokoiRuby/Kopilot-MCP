from typing import NamedTuple, Optional, Dict, Any, Union
from kubernetes import client  # type: ignore
from kubernetes.dynamic.client import DynamicClient  # type: ignore
from kubernetes.dynamic.resource import Resource as DynamicResource  # type: ignore


class GroupVersionResource(NamedTuple):
    Group: str
    Version: str
    Resource: str

    @property
    def api_version(self) -> str:
        """Returns the API version string in the format required by Kubernetes."""
        if self.Group:
            return f"{self.Group}/{self.Version}"
        return self.Version

    @property
    def resource_path(self) -> str:
        """Returns the resource path for API requests."""
        if self.Group:
            return f"{self.Group}/{self.Version}/{self.Resource}"
        return f"{self.Version}/{self.Resource}"


class Resource:
    def __init__(self, GVR: GroupVersionResource, Namespaced: bool):
        self.GVR = GVR
        self.Namespaced = Namespaced
        self._dynamic_resource_cache: Dict[str, DynamicResource] = {}

    def get_dynamic_resource(self, api_client: Union[client.ApiClient, DynamicClient]) -> DynamicResource:
        """Get a dynamic resource client for this resource.

        Args:
            api_client: Either a kubernetes.client.ApiClient or kubernetes.dynamic.DynamicClient

        Returns:
            A dynamic resource client for this resource
        """
        # Create a cache key based on the client's configuration
        cache_key = str(id(api_client))

        # Return cached resource if available
        if cache_key in self._dynamic_resource_cache:
            return self._dynamic_resource_cache[cache_key]

        # Convert ApiClient to DynamicClient if needed
        dynamic_client = api_client
        if isinstance(api_client, client.ApiClient):
            dynamic_client = DynamicClient(api_client)

        # Get the dynamic resource
        dynamic_resource = dynamic_client.resources.get(
            api_version=self.GVR.api_version,
            kind=self.get_kind(),
            name=self.GVR.Resource
        )

        # Cache the resource
        self._dynamic_resource_cache[cache_key] = dynamic_resource

        return dynamic_resource

    def get_kind(self) -> str:
        """Attempts to derive the Kind from the Resource name.

        This is a best-effort approach as there's no definitive mapping.
        For custom resources, you may need to override this method.
        """
        # Common special cases
        special_cases = {
            "endpoints": "Endpoints",
            "services": "Service",
            "pods": "Pod",
            "configmaps": "ConfigMap",
            "namespaces": "Namespace",
            "deployments": "Deployment",
            "replicasets": "ReplicaSet",
            "statefulsets": "StatefulSet",
            "daemonsets": "DaemonSet",
            "jobs": "Job",
            "cronjobs": "CronJob",
            "ingresses": "Ingress",
            "secrets": "Secret",
            "serviceaccounts": "ServiceAccount",
            "persistentvolumes": "PersistentVolume",
            "persistentvolumeclaims": "PersistentVolumeClaim",
        }

        if self.GVR.Resource in special_cases:
            return special_cases[self.GVR.Resource]

        # General case: convert to singular and capitalize
        # This is a simple approach and may not work for all resources
        resource = self.GVR.Resource
        if resource.endswith("s"):
            resource = resource[:-1]
        elif resource.endswith("ies"):
            resource = resource[:-3] + "y"

        return resource.capitalize()


resource_map = {
    "pods": Resource(GVR=GroupVersionResource(Group="", Version="v1", Resource="pods"), Namespaced=True),
    "services": Resource(GVR=GroupVersionResource(Group="", Version="v1", Resource="services"), Namespaced=True),
    "deployments": Resource(GVR=GroupVersionResource(Group="apps", Version="v1", Resource="deployments"), Namespaced=True),
    "namespaces": Resource(GVR=GroupVersionResource(Group="", Version="v1", Resource="namespaces"), Namespaced=False),
    "bindings": Resource(GVR=GroupVersionResource(Group="", Version="v1", Resource="bindings"), Namespaced=True),
    "componentstatuses": Resource(GVR=GroupVersionResource(Group="", Version="v1", Resource="componentstatuses"), Namespaced=False),
    "configmaps": Resource(GVR=GroupVersionResource(Group="", Version="v1", Resource="configmaps"), Namespaced=True),
    "endpoints": Resource(GVR=GroupVersionResource(Group="", Version="v1", Resource="endpoints"), Namespaced=True),
    "events": Resource(GVR=GroupVersionResource(Group="", Version="v1", Resource="events"), Namespaced=True),
    "limitranges": Resource(GVR=GroupVersionResource(Group="", Version="v1", Resource="limitranges"), Namespaced=True),
    "nodes": Resource(GVR=GroupVersionResource(Group="", Version="v1", Resource="nodes"), Namespaced=False),
    "persistentvolumeclaims": Resource(GVR=GroupVersionResource(Group="", Version="v1", Resource="persistentvolumeclaims"), Namespaced=True),
    "persistentvolumes": Resource(GVR=GroupVersionResource(Group="", Version="v1", Resource="persistentvolumes"), Namespaced=False),
    "podtemplates": Resource(GVR=GroupVersionResource(Group="", Version="v1", Resource="podtemplates"), Namespaced=True),
    "replicationcontrollers": Resource(GVR=GroupVersionResource(Group="", Version="v1", Resource="replicationcontrollers"), Namespaced=True),
    "resourcequotas": Resource(GVR=GroupVersionResource(Group="", Version="v1", Resource="resourcequotas"), Namespaced=True),
    "secrets": Resource(GVR=GroupVersionResource(Group="", Version="v1", Resource="secrets"), Namespaced=True),
    "serviceaccounts": Resource(GVR=GroupVersionResource(Group="", Version="v1", Resource="serviceaccounts"), Namespaced=True),
    "challenges": Resource(GVR=GroupVersionResource(Group="acme.cert-manager.io", Version="v1", Resource="challenges"), Namespaced=True),
    "orders": Resource(GVR=GroupVersionResource(Group="acme.cert-manager.io", Version="v1", Resource="orders"), Namespaced=True),
    "mutatingwebhookconfigurations": Resource(GVR=GroupVersionResource(Group="admissionregistration.k8s.io", Version="v1", Resource="mutatingwebhookconfigurations"), Namespaced=False),
    "validatingadmissionpolicies": Resource(GVR=GroupVersionResource(Group="admissionregistration.k8s.io", Version="v1", Resource="validatingadmissionpolicies"), Namespaced=False),
    "validatingadmissionpolicybindings": Resource(GVR=GroupVersionResource(Group="admissionregistration.k8s.io", Version="v1", Resource="validatingadmissionpolicybindings"), Namespaced=False),
    "validatingwebhookconfigurations": Resource(GVR=GroupVersionResource(Group="admissionregistration.k8s.io", Version="v1", Resource="validatingwebhookconfigurations"), Namespaced=False),
    "customresourcedefinitions": Resource(GVR=GroupVersionResource(Group="apiextensions.k8s.io", Version="v1", Resource="customresourcedefinitions"), Namespaced=False),
    "apiservices": Resource(GVR=GroupVersionResource(Group="apiregistration.k8s.io", Version="v1", Resource="apiservices"), Namespaced=False),
    "applications": Resource(GVR=GroupVersionResource(Group="application.aiops.com", Version="v1", Resource="applications"), Namespaced=True),
    "controllerrevisions": Resource(GVR=GroupVersionResource(Group="apps", Version="v1", Resource="controllerrevisions"), Namespaced=True),
    "daemonsets": Resource(GVR=GroupVersionResource(Group="apps", Version="v1", Resource="daemonsets"), Namespaced=True),
    "replicasets": Resource(GVR=GroupVersionResource(Group="apps", Version="v1", Resource="replicasets"), Namespaced=True),
    "statefulsets": Resource(GVR=GroupVersionResource(Group="apps", Version="v1", Resource="statefulsets"), Namespaced=True),
    "selfsubjectreviews": Resource(GVR=GroupVersionResource(Group="authentication.k8s.io", Version="v1", Resource="selfsubjectreviews"), Namespaced=False),
    "tokenreviews": Resource(GVR=GroupVersionResource(Group="authentication.k8s.io", Version="v1", Resource="tokenreviews"), Namespaced=False),
    "localsubjectaccessreviews": Resource(GVR=GroupVersionResource(Group="authorization.k8s.io", Version="v1", Resource="localsubjectaccessreviews"), Namespaced=True),
    "selfsubjectaccessreviews": Resource(GVR=GroupVersionResource(Group="authorization.k8s.io", Version="v1", Resource="selfsubjectaccessreviews"), Namespaced=False),
    "selfsubjectrulesreviews": Resource(GVR=GroupVersionResource(Group="authorization.k8s.io", Version="v1", Resource="selfsubjectrulesreviews"), Namespaced=False),
    "subjectaccessreviews": Resource(GVR=GroupVersionResource(Group="authorization.k8s.io", Version="v1", Resource="subjectaccessreviews"), Namespaced=False),
    "horizontalpodautoscalers": Resource(GVR=GroupVersionResource(Group="autoscaling", Version="v2", Resource="horizontalpodautoscalers"), Namespaced=True),
    "cronjobs": Resource(GVR=GroupVersionResource(Group="batch", Version="v1", Resource="cronjobs"), Namespaced=True),
    "jobs": Resource(GVR=GroupVersionResource(Group="batch", Version="v1", Resource="jobs"), Namespaced=True),
    "certificaterequests": Resource(GVR=GroupVersionResource(Group="cert-manager.io", Version="v1", Resource="certificaterequests"), Namespaced=True),
    "certificates": Resource(GVR=GroupVersionResource(Group="cert-manager.io", Version="v1", Resource="certificates"), Namespaced=True),
    "clusterissuers": Resource(GVR=GroupVersionResource(Group="cert-manager.io", Version="v1", Resource="clusterissuers"), Namespaced=False),
    "issuers": Resource(GVR=GroupVersionResource(Group="cert-manager.io", Version="v1", Resource="issuers"), Namespaced=True),
    "certificatesigningrequests": Resource(GVR=GroupVersionResource(Group="certificates.k8s.io", Version="v1", Resource="certificatesigningrequests"), Namespaced=False),
    "leases": Resource(GVR=GroupVersionResource(Group="coordination.k8s.io", Version="v1", Resource="leases"), Namespaced=True),
    "endpointslices": Resource(GVR=GroupVersionResource(Group="discovery.k8s.io", Version="v1", Resource="endpointslices"), Namespaced=True),
    "flowschemas": Resource(GVR=GroupVersionResource(Group="flowcontrol.apiserver.k8s.io", Version="v1", Resource="flowschemas"), Namespaced=False),
    "prioritylevelconfigurations": Resource(GVR=GroupVersionResource(Group="flowcontrol.apiserver.k8s.io", Version="v1", Resource="prioritylevelconfigurations"), Namespaced=False),
    "ingressclasses": Resource(GVR=GroupVersionResource(Group="networking.k8s.io", Version="v1", Resource="ingressclasses"), Namespaced=False),
    "ingresses": Resource(GVR=GroupVersionResource(Group="networking.k8s.io", Version="v1", Resource="ingresses"), Namespaced=True),
    "networkpolicies": Resource(GVR=GroupVersionResource(Group="networking.k8s.io", Version="v1", Resource="networkpolicies"), Namespaced=True),
    "runtimeclasses": Resource(GVR=GroupVersionResource(Group="node.k8s.io", Version="v1", Resource="runtimeclasses"), Namespaced=False),
    "catalogsources": Resource(GVR=GroupVersionResource(Group="operators.coreos.com", Version="v1alpha1", Resource="catalogsources"), Namespaced=True),
    "clusterserviceversions": Resource(GVR=GroupVersionResource(Group="operators.coreos.com", Version="v1alpha1", Resource="clusterserviceversions"), Namespaced=True),
    "installplans": Resource(GVR=GroupVersionResource(Group="operators.coreos.com", Version="v1alpha1", Resource="installplans"), Namespaced=True),
    "olmconfigs": Resource(GVR=GroupVersionResource(Group="operators.coreos.com", Version="v1", Resource="olmconfigs"), Namespaced=False),
    "operatorconditions": Resource(GVR=GroupVersionResource(Group="operators.coreos.com", Version="v2", Resource="operatorconditions"), Namespaced=True),
    "operatorgroups": Resource(GVR=GroupVersionResource(Group="operators.coreos.com", Version="v1", Resource="operatorgroups"), Namespaced=True),
    "operators": Resource(GVR=GroupVersionResource(Group="operators.coreos.com", Version="v1", Resource="operators"), Namespaced=False),
    "subscriptions": Resource(GVR=GroupVersionResource(Group="operators.coreos.com", Version="v1alpha1", Resource="subscriptions"), Namespaced=True),
    "packagemanifests": Resource(GVR=GroupVersionResource(Group="packages.operators.coreos.com", Version="v1", Resource="packagemanifests"), Namespaced=True),
    "poddisruptionbudgets": Resource(GVR=GroupVersionResource(Group="policy", Version="v1", Resource="poddisruptionbudgets"), Namespaced=True),
    "clusterrolebindings": Resource(GVR=GroupVersionResource(Group="rbac.authorization.k8s.io", Version="v1", Resource="clusterrolebindings"), Namespaced=False),
    "clusterroles": Resource(GVR=GroupVersionResource(Group="rbac.authorization.k8s.io", Version="v1", Resource="clusterroles"), Namespaced=False),
    "rolebindings": Resource(GVR=GroupVersionResource(Group="rbac.authorization.k8s.io", Version="v1", Resource="rolebindings"), Namespaced=True),
    "roles": Resource(GVR=GroupVersionResource(Group="rbac.authorization.k8s.io", Version="v1", Resource="roles"), Namespaced=True),
    "priorityclasses": Resource(GVR=GroupVersionResource(Group="scheduling.k8s.io", Version="v1", Resource="priorityclasses"), Namespaced=False),
    "csidrivers": Resource(GVR=GroupVersionResource(Group="storage.k8s.io", Version="v1", Resource="csidrivers"), Namespaced=False),
    "csinodes": Resource(GVR=GroupVersionResource(Group="storage.k8s.io", Version="v1", Resource="csinodes"), Namespaced=False),
    "csistoragecapacities": Resource(GVR=GroupVersionResource(Group="storage.k8s.io", Version="v1", Resource="csistoragecapacities"), Namespaced=True),
    "storageclasses": Resource(GVR=GroupVersionResource(Group="storage.k8s.io", Version="v1", Resource="storageclasses"), Namespaced=False),
    "volumeattachments": Resource(GVR=GroupVersionResource(Group="storage.k8s.io", Version="v1", Resource="volumeattachments"), Namespaced=False)
}
