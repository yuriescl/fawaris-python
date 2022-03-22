from typing import List
from fastapi import Depends
from overrides import overrides
from abc import ABC, abstractmethod

import fawaris
from fawaris.fastapi.utils import authenticate, detect_and_get_request_data

def register_routes(app, sep24_obj: fawaris.Sep24):
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
