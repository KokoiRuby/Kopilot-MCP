from mcp.server.fastmcp import FastMCP
from loguru import logger
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from scheme.scheme import parse_api_resources
from utils.clients import create_dynamic_client
from utils.models import create_chat_model
from kubernetes.client.models import V1ParamKind  # type: ignore
from kubernetes.dynamic import DynamicClient  # type: ignore
from langchain.chat_models.base import BaseChatModel, _ConfigurableModel
from config.config import config


__all__ = ("create_mcp_server", )


mcp_config = config["mcp"]


@dataclass
class MCPContext:
    scheme: dict[str, V1ParamKind] | None = None
    client: DynamicClient | None = None
    llm: BaseChatModel | _ConfigurableModel | None = None


def create_mcp_server() -> FastMCP:

    async def on_startup(mcp: FastMCP) -> None:
        logger.info("Starting MCP server...")

    async def on_shutdown(mcp: FastMCP) -> None:
        logger.info("Shutting down MCP server...")

    @asynccontextmanager
    async def mcp_server_lifespan(mcp: FastMCP) -> AsyncIterator[MCPContext]:
        await on_startup(mcp)

        # TODO: Exception handling
        scheme = await parse_api_resources()
        dynamic_client = await create_dynamic_client()
        llm = await create_chat_model()

        try:
            yield MCPContext(
                scheme=scheme,
                client=dynamic_client,
                llm=llm
            )
        finally:
            await on_shutdown(mcp)

    mcp = FastMCP(mcp_config["name"], lifespan=mcp_server_lifespan)

    return mcp
