from aiogram import Router

from raspbot.core.logging import configure_logging

router = Router()
logger = configure_logging(name=__name__)
