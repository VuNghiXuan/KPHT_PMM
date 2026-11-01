JAZZMIN_SETTINGS = {
    "site_header": "TRANG QUẢN TRỊ HỆ THỐNG",
    "site_brand": "AI & Gold",
    "site_logo": None,
    "welcome_sign": "Hệ thống Quản trị Tri thức & Nghiệp vụ ngành kim hoàn",
    "copyright": "VuNghiXuan",
    "user_avatar": None,
    "show_sidebar": True,
    "navigation_expanded": True,
    
    # Gom nhóm Sidebar theo kiến trúc KnowledgeDraft mới
    "side_menu_groups": [
        {
            "name": "TRI THỨC AI",
            "icon": "fas fa-brain",
            "models": [
                "app_knowledge.KnowledgeDraft",    # Bảng trung tâm mới (Thay cho Term & Process)
                "app_knowledge.BusinessLogicRule", # Bảng chứa công thức tính vàng
                "app_knowledge.AIPromptTemplate",  # Quản lý các mẫu Prompt cho AI
            ],
        },
        {
            "name": "DỮ LIỆU EXCEL",
            "icon": "fas fa-file-excel",
            "models": [
                "app_miner.ExcelProject",
                "app_miner.ExcelSheet",
            ],
        },
        {
            "name": "NGHIỆP VỤ VÀNG",
            "icon": "fas fa-coins",
            "models": [
                "gold_management.GoldTransaction",
                "gold_management.Supplier",
            ],
        },
    ],

    # Cập nhật Icon cho các Model mới
    "icons": {
        "auth.user": "fas fa-user-shield",
        "auth.group": "fas fa-users-cog",
        "app_knowledge.KnowledgeDraft": "fas fa-lightbulb", # Icon bóng đèn cho tri thức nháp
        "app_knowledge.BusinessLogicRule": "fas fa-microchip",
        "app_knowledge.AIPromptTemplate": "fas fa-terminal",
        "app_miner.ExcelProject": "fas fa-project-diagram",
        "gold_management.GoldTransaction": "fas fa-exchange-alt",
        "gold_management.Supplier": "fas fa-city",
    },

    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    
    "custom_css": "admin/css/custom_admin.css", 
    "use_google_fonts_cdn": True,
    "show_ui_builder": False,
}

JAZZMIN_UI_TWEAKS = {
    "theme": "flatly",
    "dark_mode_theme": None,
    "default_theme_mode": "light", # Bắt buộc để chế độ sáng
    
    "navbar_small_text": True,
    "footer_small_text": True,
    "body_small_text": True,
    "brand_small_text": False,
    
    # SỬA CHỖ NÀY: Chuyển từ navbar-dark sang trắng/sáng để CSS đè màu xanh lên
    "navbar": "navbar-white navbar-light", 
    "no_navbar_border": True,
    "navbar_fixed": True,
    
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    
    # SỬA CHỖ NÀY: Chuyển sidebar sang light (sáng) giống ảnh Django Admin gốc
    "sidebar": "sidebar-light-primary", 
    "sidebar_nav_small_text": True,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": True,
    "sidebar_nav_flat_style": True,
    
    # CHỈNH NÚT BẤM: Bỏ btn-dark, dùng btn-primary để nó ăn màu xanh theo CSS
    "button_classes": {
        "primary": "btn-sm btn-primary",
        "secondary": "btn-sm btn-outline-secondary",
        "info": "btn-sm btn-info",
        "warning": "btn-sm btn-warning",
        "danger": "btn-sm btn-danger",
        "success": "btn-sm btn-success"
    }
}