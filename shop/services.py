from django.db import OperationalError, ProgrammingError

from shop.models import AboutPageContent, LegalPageContent, StoreConfiguration


STORE_CONFIGURATION_DEFAULTS = {
    "name": "My Store",
    "tagline": "Your store tagline",
    "description": "Default store description.",
    "currency": "USD",
    "timezone": "UTC",
    "language": "en",
    "tax": 0,
}

LEGAL_PAGE_CONTENT_DEFAULTS = {
    "privacy_policy": "Default privacy policy content.",
    "terms_and_conditions": "Default terms and conditions content.",
}

ABOUT_PAGE_CONTENT_DEFAULTS = {
    "left_text_content": "",
    "right_text_content": "",
    "story_title": "Our Story",
    "story_content": "",
    "served_customer_count": 0,
    "sold_count": 0,
    "styles_count": 0,
    "detail_section_title": "",
    "detail_1_title": "",
    "detail_2_title": "",
    "detail_3_title": "",
}


def ensure_singleton_defaults():
    try:
        if not StoreConfiguration.objects.exists():
            StoreConfiguration.objects.create(**STORE_CONFIGURATION_DEFAULTS)
        if not LegalPageContent.objects.exists():
            LegalPageContent.objects.create(**LEGAL_PAGE_CONTENT_DEFAULTS)
        if not AboutPageContent.objects.exists():
            AboutPageContent.objects.create(**ABOUT_PAGE_CONTENT_DEFAULTS)
    except (ProgrammingError, OperationalError):
        # Tables may not exist yet during early startup or before migrations run.
        return


__all__ = [
    "ABOUT_PAGE_CONTENT_DEFAULTS",
    "LEGAL_PAGE_CONTENT_DEFAULTS",
    "STORE_CONFIGURATION_DEFAULTS",
    "ensure_singleton_defaults",
]
