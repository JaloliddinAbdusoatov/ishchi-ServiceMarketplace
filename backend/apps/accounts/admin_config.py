from django.contrib.admin.apps import AdminConfig


class MarketplaceAdminConfig(AdminConfig):
    default_site = "apps.accounts.admin_site.MarketplaceAdminSite"
