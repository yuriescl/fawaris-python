from typing import Optional, Callable, Any, Union
from abc import ABC, abstractmethod
from pydantic import BaseModel
from fawaris.models import (
    Sep9Customer,
    Transaction,
    Sep24DepositPostRequest,
    Sep24DepositPostResponse,
    Sep24AuthenticationRequiredResponse,
)
from fawaris.sep10 import Sep10Token


class Sep24(ABC):
    jwt_key: str
    log: Callable[[str], Any]

    def __init__(
        self,
        jwt_key: str,
        log: Optional[Callable[[str], Any]] = lambda msg: None,
    ):
        self.jwt_key = jwt_key
        self.log = log

    async def http_post_transactions_deposit_interactive(
        self, request: Sep24DepositPostRequest, sep10_encoded_jwt: str
    ) -> Union[Sep24DepositPostResponse, Sep24AuthenticationRequiredResponse]:
        try:
            sep10_token = Sep10Token(sep10_encoded_jwt, self.jwt_key)
        except ValueError as e:
            self.log(str(e))
            return Sep24AuthenticationRequiredResponse()
        tx = await self.create_transaction(request, sep10_token)
        url = await self.get_interactive_url(request, sep10_token, tx)
        return Sep24DepositPostResponse(
            url=url,
            id=tx.id,
        )

    @abstractmethod
    async def create_transaction(
        self, request: Sep24DepositPostRequest, sep10_token: Sep10Token
    ):
        raise NotImplementedError()

    @abstractmethod
    async def get_interactive_url(
        self, request: Sep24DepositPostRequest, sep10_token: Sep10Token, tx: Transaction
    ):
        raise NotImplementedError()
