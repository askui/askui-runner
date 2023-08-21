import base64

from pydantic import BaseModel


class AskUiAccessToken(BaseModel):
    access_token: str | None

    def to_base64(self) -> str:
        return (
            base64.b64encode(self.access_token.encode()).decode()
            if self.access_token
            else ""
        )

    def to_auth_header(self) -> str:
        base64_token = self.to_base64()
        return f"Basic {base64_token}"
