
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    bot_token: str
    super_admin_id: int
    webapp_url: str = "http://localhost:5173"
    cors_origins: str = "http://localhost:5173"
    upload_dir: str = "./uploads"

    use_webhook: bool = False
    webhook_url: str | None = None

    # Cloudinary configuration
    cloudinary_cloud_name: str | None = None
    cloudinary_api_key: str | None = None
    cloudinary_api_secret: str | None = None

    @property
    def cloudinary_enabled(self) -> bool:
        return bool(
            self.cloudinary_cloud_name
            and self.cloudinary_api_key
            and self.cloudinary_api_secret
        )

    @property
    def cloudinary_partially_configured(self) -> bool:
        configured = (
            self.cloudinary_cloud_name,
            self.cloudinary_api_key,
            self.cloudinary_api_secret,
        )
        return any(configured) and not all(configured)

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
