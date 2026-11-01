"""
Package settings initializer.
"""
from .base import *
from .ai_vector import *
from .celery_channels import *

# Jazzmin & Logging bổ sung trực tiếp tại đây hoặc gom nhóm
JAZZMIN_SETTINGS = {
    "site_title": "VuNghiXuan",
    "site_header": "vnxChatBot",
    "site_brand": "vnxChatBot",
    "welcome_sign": "Chào mừng đến với hệ thống quản trị",
    # "custom_css": "css/ledger_theme.css",
    "custom_css": "css/admin_custom.css",
    "theme": "flatly",
    "show_sidebar": True,
    "navigation_expanded": True,
}

JAZZMIN_UI_TWEAKS = {
    "navbar_fixed": True,
    "sidebar_fixed": True,
    "layout_boxed": False,
    "sidebar": "sidebar-dark-primary",
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'debug_vnx.log'),
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        'console': {
            'level': 'WARNING',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'apps': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}