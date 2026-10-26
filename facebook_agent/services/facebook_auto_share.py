# Re-export core facebook_auto_share functions
from core.services.facebook_auto_share import (
    get_facebook_page_credentials,
    get_daily_shared_count,
    build_aeo_message,
    should_share,
    share_premium_to_facebook_page,
    execute_premium_share,
    trigger_async_share_premium,
)

__all__ = [
    "get_facebook_page_credentials",
    "get_daily_shared_count",
    "build_aeo_message",
    "should_share",
    "share_premium_to_facebook_page",
    "execute_premium_share",
    "trigger_async_share_premium",
]
