import asyncio
from typing import Optional, Callable, Any, Union, List
from abc import ABC, abstractmethod
from pydantic import BaseModel
from fawaris.models import (
    Sep9Customer,
    Sep24TransactionStatus,
    Sep24Transaction,
    Sep24DepositPostRequest,
    Sep24WithdrawPostRequest,
    Sep24PostResponse,
    Sep24InfoRequest,
    Sep24InfoResponse,
    Sep24FeeRequest,
    Sep24FeeResponse,
    Sep24TransactionsGetRequest,
    Sep24TransactionsGetResponse,
    Sep24TransactionGetRequest,
    Sep24TransactionGetResponse,
)
from fawaris.exceptions import Sep10InvalidToken
from fawaris.sep10 import Sep10Token


try:
    from databases import Database
    from fawaris.databases import tables
except ImportError:
    Database = None


class BaseSep24(ABC):
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
        self, request: Sep24DepositPostRequest, token: Sep10Token
    ) -> Sep24PostResponse:
        tx = await self.create_transaction(request, token)
        url = await self.get_interactive_url(request, token, tx)
        return Sep24PostResponse(
            url=url,
            id=tx.id,
        )

    async def http_post_transactions_withdraw_interactive(
        self, request: Sep24WithdrawPostRequest, token: Sep10Token
    ) -> Sep24PostResponse:
        tx = await self.create_transaction(request, token)
        url = await self.get_interactive_url(request, token, tx)
        return Sep24PostResponse(
            url=url,
            id=tx.id,
        )

    async def task_all(self) -> None:
        coroutines = [
            self.task_poll_deposits_to_receive(),
            self.task_send_deposits(),
            self.task_poll_withdrawals_to_receive(),
            self.task_poll_withdrawals_sent(),
            self.task_send_withdrawals(),
        ]
        await asyncio.gather(*coroutines)

    async def task_poll_deposits_to_receive(self) -> None:
        deposits_to_receive = await self.get_transactions(
            kind="deposit", status="pending_user_transfer_start"
        )
        coroutines = [
            self.is_deposit_received(deposit) for deposit in deposits_to_receive
        ]
        results = await asyncio.gather(*coroutines)
        received_deposits = []
        for deposit, received in zip(deposits_to_receive, results):
            if received is True:
                received_deposits.append(deposit)
        await self.update_transactions(received_deposits, status="pending_anchor")

    async def task_send_deposits(self) -> None:
        deposits_received = await self.get_transactions(
            kind="deposit", status="pending_anchor"
        )
        coroutines = [self.send_deposit(deposit) for deposit in deposits_received]
        await asyncio.gather(*coroutines)

    async def task_poll_withdrawals_to_receive(self) -> None:
        pass  # TODO

    async def task_poll_withdrawals_sent(self) -> None:
        withdrawals_sent = await self.get_transactions(
            kind="withdrawal", status="pending_external"
        )
        coroutines = [
            self.is_withdrawal_complete(withdrawal) for withdrawal in withdrawals_sent
        ]
        results = await asyncio.gather(*coroutines)
        completed_withdrawals = []
        for withdrawal, completed in zip(withdrawals_sent, results):
            if completed is True:
                completed_withdrawals.append(withdrawal)
        await self.update_transactions(completed_withdrawals, status="completed")

    async def task_send_withdrawals(self) -> None:
        withdrawals_received = await self.get_transactions(
            kind="withdrawal", status="pending_anchor"
        )
        coroutines = [
            self.send_withdrawal(withdrawal) for withdrawal in withdrawals_received
        ]
        await asyncio.gather(*coroutines)

    @abstractmethod
    async def http_get_info(self, request: Sep24InfoRequest) -> Sep24InfoResponse:
        raise NotImplementedError()

    @abstractmethod
    async def http_get_fee(
        self, request: Sep24FeeRequest, token: Optional[Sep10Token] = None
    ) -> Sep24FeeResponse:
        raise NotImplementedError()

    @abstractmethod
    async def http_get_transactions(
        self, request: Sep24TransactionsGetRequest, token: Sep10Token
    ) -> Sep24TransactionsGetResponse:
        raise NotImplementedError()

    @abstractmethod
    async def http_get_transaction(
        self, request: Sep24TransactionGetRequest, token: Sep10Token
    ) -> Sep24TransactionGetResponse:
        raise NotImplementedError()

    @abstractmethod
    async def create_transaction(
        self,
        request: Union[Sep24DepositPostRequest, Sep24WithdrawPostRequest],
        token: Sep10Token,
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def get_interactive_url(
        self,
        request: Union[Sep24DepositPostRequest, Sep24WithdrawPostRequest],
        token: Sep10Token,
        tx: Sep24Transaction,
    ) -> str:
        raise NotImplementedError()

    @abstractmethod
    async def get_transactions(self, **filters) -> List[Sep24Transaction]:
        raise NotImplementedError()

    @abstractmethod
    async def is_deposit_received(self, deposit: Sep24Transaction) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def is_withdrawal_complete(self, withdrawal: Sep24Transaction) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def update_transactions(self, transactions: List[Sep24Transaction], **values):
        raise NotImplementedError()

    @abstractmethod
    async def send_withdrawal(self, withdrawal: Sep24Transaction) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def send_deposit(self, deposit: Sep24Transaction) -> None:
        raise NotImplementedError()


if Database is not None:

    class DatabaseSep24(ABC):
        sep10_jwt_key: str
        database: Database
        log: Callable[[str], Any]

        def __init__(
            self,
            sep10_jwt_key: str,
            database: Database,
            log: Optional[Callable[[str], Any]] = lambda msg: None,
        ):
            self.sep10_jwt_key = sep10_jwt_key
            self.database = database
            self.log = log

        async def http_post_transactions_deposit_interactive(
            self, request: Sep24DepositPostRequest, token: Sep10Token
        ) -> Sep24PostResponse:
            tx = await self.create_transaction(request, token)
            url = await self.get_interactive_url(request, token, tx)
            return Sep24PostResponse(
                url=url,
                id=tx.id,
            )

        async def http_post_transactions_withdraw_interactive(
            self, request: Sep24WithdrawPostRequest, token: Sep10Token
        ) -> Sep24PostResponse:
            tx = await self.create_transaction(request, token)
            url = await self.get_interactive_url(request, token, tx)
            return Sep24PostResponse(
                url=url,
                id=tx.id,
            )

        async def task_all(self) -> None:
            coroutines = [
                self.task_poll_deposits_to_receive(),
                self.task_send_deposits(),
                self.task_poll_withdrawals_to_receive(),
                self.task_poll_withdrawals_sent(),
                self.task_send_withdrawals(),
            ]
            await asyncio.gather(*coroutines)

        async def task_poll_deposits_to_receive(self) -> None:
            deposits_to_receive = await self.get_transactions(
                kind="deposit", status="pending_user_transfer_start"
            )
            coroutines = [
                self.is_deposit_received(deposit) for deposit in deposits_to_receive
            ]
            results = await asyncio.gather(*coroutines)
            received_deposits = []
            for deposit, received in zip(deposits_to_receive, results):
                if received is True:
                    received_deposits.append(deposit)
            await self.update_transactions(received_deposits, status="pending_anchor")

        async def task_send_deposits(self) -> None:
            deposits_received = await self.get_transactions(
                kind="deposit", status="pending_anchor"
            )
            coroutines = [self.send_deposit(deposit) for deposit in deposits_received]
            await asyncio.gather(*coroutines)

        async def task_poll_withdrawals_to_receive(
            self, last_checked_tx_hash: Optional[str] = None
        ) -> None:
            pass  # TODO

        async def task_poll_withdrawals_sent(self) -> None:
            withdrawals_sent = await self.get_transactions(
                kind="withdrawal", status="pending_external"
            )
            coroutines = [
                self.is_withdrawal_complete(withdrawal)
                for withdrawal in withdrawals_sent
            ]
            results = await asyncio.gather(*coroutines)
            completed_withdrawals = []
            for withdrawal, completed in zip(withdrawals_sent, results):
                if completed is True:
                    completed_withdrawals.append(withdrawal)
            await self.update_transactions(completed_withdrawals, status="completed")

        async def task_send_withdrawals(self) -> None:
            withdrawals_received = await self.get_transactions(
                kind="withdrawal", status="pending_anchor"
            )
            coroutines = [
                self.send_withdrawal(withdrawal) for withdrawal in withdrawals_received
            ]
            await asyncio.gather(*coroutines)

        async def create_transaction(
            self,
            request: Union[Sep24DepositPostRequest, Sep24WithdrawPostRequest],
            token: Sep10Token,
        ) -> None:
            query = tables.sep24_transactions.insert()
            transaction = await self.create_transaction_object(request, token)
            await self.database.execute(query=query, values=transaction.dict())

        async def get_transactions(self, **filters) -> List[Sep24Transaction]:
            query = tables.sep24_transactions.select()
            results = await self.database.fetch_all(query, dict(filters))

        async def update_transactions(
            self, transactions: List[Sep24Transaction], **values
        ):
            ids = [transaction.id for transaction in transactions]
            query = (
                tables.sep24_transactions.update()
                .where(tables.sep24_transactions.c.id.in_(ids))
                .values(dict(values))
            )
            await self.database.execute(query)

        async def send_deposit(self, deposit: Sep24Transaction) -> None:
            pass  # TODO

        @abstractmethod
        async def http_get_info(self, request: Sep24InfoRequest) -> Sep24InfoResponse:
            raise NotImplementedError()

        @abstractmethod
        async def http_get_fee(
            self, request: Sep24FeeRequest, token: Optional[Sep10Token] = None
        ) -> Sep24FeeResponse:
            raise NotImplementedError()

        @abstractmethod
        async def http_get_transactions(
            self, request: Sep24TransactionsGetRequest, token: Sep10Token
        ) -> Sep24TransactionsGetResponse:
            raise NotImplementedError()

        @abstractmethod
        async def http_get_transaction(
            self, request: Sep24TransactionGetRequest, token: Sep10Token
        ) -> Sep24TransactionGetResponse:
            raise NotImplementedError()

        @abstractmethod
        async def get_interactive_url(
            self,
            request: Union[Sep24DepositPostRequest, Sep24WithdrawPostRequest],
            token: Sep10Token,
            tx: Sep24Transaction,
        ) -> str:
            raise NotImplementedError()

        @abstractmethod
        async def create_transaction_object(
            self,
            request: Union[Sep24DepositPostRequest, Sep24WithdrawPostRequest],
            token: Sep10Token,
        ) -> Sep24Transaction:
            raise NotImplementedError()

        @abstractmethod
        async def is_deposit_received(self, deposit: Sep24Transaction) -> bool:
            raise NotImplementedError()

        @abstractmethod
        async def is_withdrawal_complete(self, withdrawal: Sep24Transaction) -> bool:
            raise NotImplementedError()

        @abstractmethod
        async def send_withdrawal(self, withdrawal: Sep24Transaction) -> None:
            raise NotImplementedError()

    Sep24 = DatabaseSep24
else:
    Sep24 = BaseSep24
