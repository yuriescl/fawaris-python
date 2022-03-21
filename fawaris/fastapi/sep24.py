from typing import List
from fastapi import Depends
from overrides import overrides
from abc import ABC, abstractmethod
import fawaris
from utils import authenticate, detect_and_get_request_data

try:
    from databases import Database
    database_decorator = overrides
except ImportError:
    Database = None
    database_decorator = abstractmethod

class Sep24(fawaris.Sep24):
    def __init__(self, sep10_jwt_key, database=None, log=lambda msg: None):
        if database is not None and Database is None:
            raise ValueError("'database' parameter requires package 'databases' to be installed")
        self.database = database
        super().__init__(sep10_jwt_key, log=log)

    @overrides
    async def http_get_info(self, request) -> fawaris.Sep24InfoResponse:
        return fawaris.Sep24InfoResponse(
            deposit={
                "PURPLE": fawaris.Sep24InfoResponseDeposit(
                    enabled=True,
                    fee_fixed=5,
                    fee_percent=1,
                    min_amount=0.1,
                    max_amount=1000,
                ),
            },
            withdraw={
                "PURPLE": fawaris.Sep24InfoResponseWithdraw(
                    enabled=True,
                    fee_minimum=5,
                    fee_percent=0.5,
                    min_amount=0.1,
                    max_amount=1000,
                ),
            },
            fee=fawaris.Sep24InfoResponseFee(enabled=False),
            features=fawaris.Sep24InfoResponseFeatures(
                account_creation=False,
                claimable_balances=False,
            ),
        )

    @overrides
    async def http_get_fee(self, request, token=None) -> fawaris.Sep24FeeResponse:
        raise NotImplementedError()

    @overrides
    async def http_get_transactions(
        self, request, token
    ) -> fawaris.Sep24TransactionsGetResponse:
        return {
            "transactions": []
        }

    @overrides
    async def http_get_transaction(
        self, request, token
    ) -> fawaris.Sep24TransactionGetResponse:
        return {
            "transaction": fawaris.Transaction(
                id="transaction1",
                kind="withdrawal",
                status="pending_user_transfer_start",
            )
        }

    @database_decorator
    async def create_transaction(self, request, token):
        if self.database is None:
            raise NotImplementedError()

    @database_decorator
    async def get_transactions(**filters) -> List[fawaris.Sep24Transaction]:
        raise NotImplementedError()

    @database_decorator
    async def is_deposit_received(self, deposit: fawaris.Sep24Transaction) -> bool:
        raise NotImplementedError()

    @database_decorator
    async def is_withdrawal_complete(self, withdrawal: fawaris.Sep24Transaction) -> bool:
        raise NotImplementedError()

    @database_decorator
    async def update_transactions(self, transactions: List[fawaris.Sep24Transaction], **values):
        raise NotImplementedError()

    @database_decorator
    async def send_withdrawal(self, withdrawal: fawaris.Sep24Transaction) -> None:
        raise NotImplementedError()


def add_routes(app, sep24_obj: Sep24):
    @app.post("/sep24/transactions/deposit/interactive")
    async def http_post_transactions_deposit_interactive(
        request=Depends(authenticate(sep24_obj.sep10_jwt_key)),
    ):
        data = await detect_and_get_request_data(request)
        return await sep24_obj.http_post_transactions_deposit_interactive(
            fawaris.Sep24DepositPostRequest(**data), request.token
        )

    @app.post("/sep24/transactions/withdraw/interactive")
    async def http_post_transactions_withdraw_interactive(
        request=Depends(authenticate(sep24_obj.sep10_jwt_key)),
    ):
        data = await detect_and_get_request_data(request)
        return await sep24_obj.http_post_transactions_withdraw_interactive(
            fawaris.Sep24WithdrawPostRequest(**data), request.token
        )

    @app.get("/sep24/info")
    async def http_get_info(request):
        return await sep24_obj.http_get_info(
            fawaris.Sep24InfoRequest(**dict(request.query_params)),
        )

    @app.get("/sep24/transactions")
    async def http_get_transactions(request):
        return await sep24_obj.http_get_transactions(
            fawaris.Sep24TransactionsGetRequest(**dict(request.query_params)),
        )

    @app.get("/sep24/transaction")
    async def http_get_transaction(request):
        return await sep24_obj.http_get_transaction(
            fawaris.Sep24TransactionGetRequest(**dict(request.query_params)),
        )
