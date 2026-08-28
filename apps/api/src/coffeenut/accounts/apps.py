from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "coffeenut.accounts"
    label = "accounts"

    def ready(self) -> None:
        from . import signals  # noqa: F401
