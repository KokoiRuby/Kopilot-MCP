from typing import Union
from langchain.chat_models import init_chat_model
from langchain.chat_models.base import BaseChatModel, _ConfigurableModel
from config.config import config


__all__ = ("create_chat_model", )


llm_config = config["server"]["llm"]


async def create_chat_model() -> Union[BaseChatModel, _ConfigurableModel]:
    return init_chat_model(
        configurable_fields=("model", "model_provider",
                             "base_url", "api_key"),
        temperature=llm_config["temperature"],
    )
