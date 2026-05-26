from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from server.schema.request import APIRequest

T = TypeVar("T", bound="ClientRequest")


class ClientRequest(BaseModel, ABC, Generic[T]):
    @staticmethod
    @abstractmethod
    def build(data: APIRequest, model_name: str, isStream: bool = False) -> T:
        pass

    def args(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)
