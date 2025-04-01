from mcp.server.fastmcp import FastMCP, Context
from loguru import logger
import mcp_server_factory
from kubernetes.client.models import V1ParamKind  # type: ignore
from langchain.chat_models.base import BaseChatModel, _ConfigurableModel
from langchain_core.messages import SystemMessage, HumanMessage
from typing import Union
from config.config import config
import sys
import json


logger.configure(
    handlers=[{"sink": sys.stderr, "level": config["mcp"]["log_level"]}])

mcp = mcp_server_factory.create_mcp_server()

llm_config = config["server"]["llm"]

create_prompt: str = """You are a Kubernetes expert.
Your job is to transform Kubernetes resource manifest from user input in YAML to one-line JSON.
You may refer to Kubernetes API doccuments: https://kubernetes.io/docs/reference/kubernetes-api/ for more information.
DO NOT include the generated manifest into the code block."""

# update_prompt: str = """You are a Kubernetes expert.
# You job is to merge the exsisting manifest with the patch provided from user input into a new json patch.
# You may refer to Kubernetes API doccuments: https://kubernetes.io/docs/reference/kubernetes-api/ for more information.
# You should focus on the `spec` and `metadata` fields of the manifest. You don't need to consider the `status` field.
# When you're dealing with `metadata` fields:
# 1. Skip `managedFields`.
# 2. Remove key/value if you are asked to remove a label or annotation.
# DO NOT include the generated manifest into the code block."""


# @mcp.tool()
# def test_ctx(ctx: Context) -> str:
#     """
#     Test the context.

#     Args:
#         ctx (Context): The context.

#     Returns:
#         dict[str, V1ParamKind] | None: The scheme from the context.
#     """
#     if not (lc := ctx.request_context.lifespan_context):
#         return ""
#     logger.debug(f"Scheme: {lc.scheme}")
#     return len(lc.scheme.keys())


def __send_message(llm: Union[BaseChatModel, _ConfigurableModel], prompt: str, input: str) -> Union[str, list[Union[str, dict]]]:
    """
    Send a message to the LLM.

    Args:
        llm (Context): The LLM context.
        input (str): The original user input message.

    Returns:
        str: The response from the LLM.
    """
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=input),
    ]
    response = llm.invoke(
        messages,
        config={
            "configurable": {
                "model_provider": llm_config["model_provider"],
                "base_url": llm_config["base_url"],
                "api_key": llm_config["api_key"],
                "model": llm_config["model"],
            }
        }
    )
    return response.content


@mcp.tool()
def create_resource(ctx: Context, resource: str, manifest_yaml: str, namespace: str = "") -> str:
    """
    Create a resource in a namespace.

    Args:
        ctx (Context): MCP server context.
        resource (str): The kubernetes resource to create.
        manifest_yaml (str): The kubernetes resource manifest in yaml.
        namespace (str): The kubernetes namespace where the resource is.

    Returns:
        str: The result of the creation.
    """
    if not (lc := ctx.request_context.lifespan_context) or not (client := lc.client) or not (scheme := lc.scheme) or not (llm := lc.llm):
        return "Context is missing."

    if not resource:
        return "Resource is null."

    if not resource in scheme.keys():
        return "Invalid resource. Please run `kubectl api-resources` to get supported API resources on the server."

    logger.debug(
        f"Create the [{resource}] in namespace [{namespace}] with manifest:\n{manifest_yaml}")

    manifest_json_str = __send_message(
        llm, prompt=create_prompt, input=manifest_yaml)
    logger.debug(f"Manifest:\n{manifest_json_str}")

    # Validate and parse JSON manifest
    try:
        # Parse the JSON string into a Python dictionary
        manifest_json = json.loads(manifest_json_str) if isinstance(
            manifest_json_str, str) else manifest_json_str
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON manifest: {e}")
        sys.exit(1)

    api = client.resources.get(
        api_version=scheme[resource].gvk.api_version,
        kind=scheme[resource].gvk.kind,
    )

    try:
        response = api.create(body=manifest_json, namespace=namespace)
    except Exception as e:
        logger.error(f"Error creating resource: {e}")
        sys.exit(1)

    logger.debug(f"Created response: {response}")

    return f"Create [{resource}] in namespace [{namespace}] successfully."


# TODO: Error if str type hint on patch parameter, else if dict type hint on patch parameter, then function will not be called
# Tool result: meta=None content=[TextContent(type='text', text="Error executing tool update_resource: 1 validation error for update_resourceArguments
# patch
# Input should be a valid string [type=string_type, input_value={'metadata': {'labels': {'app': 'busybox'}}}, input_type=dict]    For further information visit https://errors.pydantic.dev/2.8/v/string_type", annotations=None)] isError=True
@mcp.tool()
def update_resource(ctx: Context, resource: str, name: str, patch, namespace: str = "") -> str:
    """
    Update a resource in a namespace.

    Args:
        ctx (Context): MCP server context.
        resource (str): The kubernetes resource to update.
        name (str): The name of the resource to update.
        patch: The patch to apply to the resource.
        namespace (str): The kubernetes namespace where the resource is.

    Returns:
        str: The result of the update.
    """
    if not (lc := ctx.request_context.lifespan_context) or not (client := lc.client) or not (scheme := lc.scheme) or not (llm := lc.llm):
        return "Context is missing."

    if not resource:
        return "Resource is null."

    if not resource in scheme.keys():
        return "Invalid resource. Please run `kubectl api-resources` to get supported API resources on the server."

    logger.debug(
        f"Update the [{resource}] named [{name}] in namespace [{namespace}] given patch:\n{patch}")

    api = client.resources.get(
        api_version=scheme[resource].gvk.api_version,
        kind=scheme[resource].gvk.kind,
    )

    # Get the resource by name
    try:
        if scheme[resource].is_namespaced:
            _ = api.get(namespace=namespace, name=name)
        else:
            _ = api.get(name=name)
    except Exception as e:
        logger.error(f"Error getting resource: {e}")
        sys.exit(1)

    try:
        if scheme[resource].is_namespaced:
            response = api.patch(name=name, body=patch,
                                 content_type="application/merge-patch+json",
                                 namespace=namespace)
        else:
            response = api.patch(name=name, body=patch,
                                 content_type="application/merge-patch+json")
    except Exception as e:
        logger.error(f"Error patching resource: {e}")

    logger.debug(f"Updated response: {response}")

    return f"Update [{resource}] in namespace [{namespace}] successfully."


@mcp.tool()
def get_resources(ctx: Context, resource: str, namespace: str = "") -> str:
    """
    Get a list of resources in a namespace.

    Args:
        ctx (Context): MCP server context.
        resource (str): The kubernetes resource to get.
        namespace (str): The kubernetes namespace where the resource is.

    Returns:
        str: The list of resources in namespace.
    """
    if not (lc := ctx.request_context.lifespan_context) or not (client := lc.client) or not (scheme := lc.scheme):
        return "Context is missing."

    if not resource:
        return "Resource is null."

    if not resource in scheme.keys():
        return "Invalid resource. Please run `kubectl api-resources` to get supported API resources on the server."

    logger.debug(f"Get the list of [{resource}] in namespace [{namespace}]")

    api = client.resources.get(
        api_version=scheme[resource].gvk.api_version,
        kind=scheme[resource].gvk.kind,
    )

    try:
        if scheme[resource].is_namespaced:
            resources = api.get(namespace=namespace)
        else:
            resources = api.get()
    except Exception as e:
        logger.error(f"Error getting resource: {e}")
        sys.exit(1)

    # TODO: Simply return the name list of resources
    # Perhaps subprocess kubectl directly would get better output instead of formatting output right here,
    output = [f"{'NAME'}"]
    for res in resources.items:
        name = res.metadata.name
        output.append(f"{name}")

    return '\n'.join(output)


@mcp.tool()
def get_resource(ctx: Context, resource: str, name: str, namespace: str = "") -> str:
    """
    Get a resource in a namespace by name.

    Args:
        ctx (Context): MCP server context.
        resource (str): The kubernetes resource to get.
        name (str): The name of the resource to get.
        namespace (str): The kubernetes namespace where the resource is.

    Returns:
        str: The resource in namespace.
    """
    if not (lc := ctx.request_context.lifespan_context) or not (client := lc.client) or not (scheme := lc.scheme):
        return "Context is missing."

    if not resource:
        return "Resource is null."

    if not resource in scheme.keys():
        return "Invalid resource. Please run `kubectl api-resources` to get supported API resources on the server."

    if not name:
        return "Name is null."

    logger.debug(
        f"Get the [{resource}] named [{name}] in namespace [{namespace}]")

    api = client.resources.get(
        api_version=scheme[resource].gvk.api_version,
        kind=scheme[resource].gvk.kind,
    )

    try:
        if scheme[resource].is_namespaced:
            resource = api.get(namespace=namespace, name=name)
        else:
            resource = api.get(name=name)
    except Exception as e:
        logger.error(f"Error getting resource: {e}")
        sys.exit(1)

    output = [f"{'NAME'}"]
    output.append(f"{resource.metadata.name}")

    return '\n'.join(output)


@mcp.tool()
def delete_resource(ctx: Context, resource: str, name: str, namespace: str = "") -> str:
    """
    Delete a resource in a namespace.

    Args:
        ctx (Context): MCP server context.
        resource (str): The kubernetes resource to delete.
        namespace (str): The kubernetes namespace where the resource is.
        name (str): The name of the resource to delete.

    Returns:
        str: The result of the deletion.
    """
    if not (lc := ctx.request_context.lifespan_context) or not (client := lc.client) or not (scheme := lc.scheme):
        return "Context is missing."

    if not resource:
        return "Resource is null."

    if not resource in scheme.keys():
        return "Invalid resource. Please run `kubectl api-resources` to get supported API resources on the server."

    if not name:
        return "Name is null."

    logger.debug(
        f"Delete the [{resource}] [{name}] in namespace [{namespace}]")

    api = client.resources.get(
        api_version=scheme[resource].gvk.api_version,
        kind=scheme[resource].gvk.kind,
    )

    try:
        if scheme[resource].is_namespaced:
            api.delete(namespace=namespace, name=name)
        else:
            api.delete(name=name)
    except Exception as e:
        logger.error(f"Error deleting resource: {e}")
        sys.exit(1)

    return f"Delete [{resource}] [{name}] in namespace [{namespace}] successfully."


if __name__ == "__main__":
    mcp.run(transport="stdio")
