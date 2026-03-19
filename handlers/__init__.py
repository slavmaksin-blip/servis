from handlers.start import router as start_router
from handlers.modules import router as modules_router
from handlers.shop import router as shop_router
from handlers.profile import router as profile_router
from handlers.admin import router as admin_router
from handlers.help import router as help_router

__all__ = [
    "start_router",
    "modules_router",
    "shop_router",
    "profile_router",
    "admin_router",
    "help_router",
]
