from pydantic import BaseModel

class AppConfig(BaseModel):
    db_echo: bool = False

CONFIG = AppConfig()
