from typing import Optional, Callable, Any, Union
from abc import ABC, abstractmethod
from pydantic import BaseModel
from fawaris.models import (
    Sep9Customer,
    Transaction,
    Sep24DepositPostRequest,
    Sep24WithdrawPostRequest,
    Sep24PostResponse,
    Sep24InfoRequest,
    Sep24InfoResponse,
    Sep24FeeRequest,
    Sep24FeeResponse,
)
from fawaris.exceptions import Sep10InvalidToken
from fawaris.sep10 import Sep10Token


class Sep24(ABC):
    sep10_jwt_key: str
    log: Callable[[str], Any]

    def __init__(
        self,
        sep10_jwt_key: str,
        log: Optional[Callable[[str], Any]] = lambda msg: None,
    ):
        self.sep10_jwt_key = sep10_jwt_key
        self.log = log

    async def http_post_transactions_deposit_interactive(
        self, request: Sep24DepositPostRequest, sep10_encoded_jwt: str
    ) -> Sep24PostResponse:
        try:
            sep10_token = Sep10Token(sep10_encoded_jwt, self.sep10_jwt_key)
        except ValueError as e:
            raise Sep10InvalidToken(e)
        tx = await self.create_transaction(request, sep10_token)
        url = await self.get_interactive_url(request, sep10_token, tx)
        return Sep24PostResponse(
            url=url,
            id=tx.id,
        )

    async def http_post_transactions_withdraw_interactive(
        self, request: Sep24WithdrawPostRequest, sep10_encoded_jwt: str
    ) -> Sep24PostResponse:
        try:
            sep10_token = Sep10Token(sep10_encoded_jwt, self.sep10_jwt_key)
        except ValueError as e:
            raise Sep10InvalidToken(e)
        tx = await self.create_transaction(request, sep10_token)
        url = await self.get_interactive_url(request, sep10_token, tx)
        return Sep24PostResponse(
            url=url,
            id=tx.id,
        )

    @abstractmethod
    async def http_get_info(self, request: Sep24InfoRequest) -> Sep24InfoResponse:
        raise NotImplementedError()

    @abstractmethod
    async def http_get_fee(
        self, request: Sep24FeeRequest, sep10_encoded_jwt: Optional[str] = None
    ) -> Sep24FeeResponse:
        raise NotImplementedError()

    @abstractmethod
    async def create_transaction(
        self,
        request: Union[Sep24DepositPostRequest, Sep24WithdrawPostRequest],
        sep10_token: Sep10Token,
    ):
        raise NotImplementedError()

    @abstractmethod
    async def get_interactive_url(
        self,
        request: Union[Sep24DepositPostRequest, Sep24WithdrawPostRequest],
        sep10_token: Sep10Token,
        tx: Transaction,
    ):
        raise NotImplementedError()
