from aiogram import Router
from bot.handlers.start import router as start_router
from bot.handlers.user import router as user_router
from bot.handlers.admin import router as admin_router
from bot.handlers.group import router as group_router
from bot.handlers.poll_answer import router as poll_answer_router

main_router = Router()
main_router.include_router(start_router)
main_router.include_router(user_router)
main_router.include_router(admin_router)
main_router.include_router(group_router)
main_router.include_router(poll_answer_router)

__all__ = ["main_router"]
