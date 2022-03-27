import asyncio
from typing import Optional, Callable, Any, Union, List, Dict, Tuple
from abc import ABC, abstractmethod
import logging
from pydantic import BaseModel
from stellar_sdk.client.aiohttp_client import AiohttpClient
from stellar_sdk import ServerAsync, TransactionEnvelope
from stellar_sdk.transaction import Transaction as HorizonTransaction
from stellar_sdk.exceptions import (
    NotFoundError,
)
from stellar_sdk.xdr.utils import from_xdr_amount
from stellar_sdk.xdr import (
    PaymentResult,
    PathPaymentStrictSendResult,
    PathPaymentStrictReceiveResult,
    OperationResult,
    TransactionResult,
)
from stellar_sdk.operation import (
    Operation,
    Payment,
    PathPaymentStrictReceive,
    PathPaymentStrictSend,
)

from fawaris.models import (
    Sep9Customer,
    Sep24TransactionKind,
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
    Asset,
)
from fawaris.sep10 import Sep10Token

PaymentOpResult = Union[
    PaymentResult, PathPaymentStrictSendResult, PathPaymentStrictReceiveResult
]
PaymentOp = Union[Payment, PathPaymentStrictReceive, PathPaymentStrictSend]


logger = logging.getLogger(__name__)


class Sep24(ABC):
    sep10_jwt_secret: str
    horizon_url: str
    network_passphrase: str
    assets: Dict[str, Asset]

    def __init__(
        self,
        sep10_jwt_secret: str,
        horizon_url: str,
        network_passphrase: str,
        assets: Dict[str, Asset],
    ):
        self.sep10_jwt_secret = sep10_jwt_secret
        self.horizon_url = horizon_url
        self.network_passphrase = network_passphrase
        self.assets = assets

    async def http_post_transactions_deposit_interactive(
        self, request: Sep24DepositPostRequest, token: Sep10Token
    ) -> Sep24PostResponse:
        info = await self.http_get_info(Sep24InfoRequest(lang=request.lang))
        try:
            if not info["deposit"][request.asset_code].enabled:
                raise KeyError()
        except KeyError:
            raise ValueError(f"Deposit is not enabled for asset {request.asset_code}")
        tx = await self.create_transaction(request, token)
        url = await self.get_interactive_url(request, token, tx)
        return Sep24PostResponse(
            url=url,
            id=tx.id,
        )

    async def http_post_transactions_withdraw_interactive(
        self, request: Sep24WithdrawPostRequest, token: Sep10Token
    ) -> Sep24PostResponse:
        info = await self.http_get_info(Sep24InfoRequest(lang=request.lang))
        try:
            if not info["withdraw"][request.asset_code].enabled:
                raise KeyError()
        except KeyError:
            raise ValueError(f"Withdrawal is not enabled for asset {request.asset_code}")
        tx = await self.create_transaction(request, token)
        url = await self.get_interactive_url(request, token, tx)
        return Sep24PostResponse(
            url=url,
            id=tx.id,
        )

    async def task_all(self) -> None:
        print("running task_all")
        coroutines = [
            self.task_poll_deposits_to_receive(),
            self.task_send_deposits(),
            self.task_poll_withdrawals_sent(),
            self.task_send_withdrawals(),
        ]
        results = await asyncio.gather(*coroutines)

    async def task_poll_deposits_to_receive(self) -> None:
        deposits_to_receive = await self.get_transactions(
            kind="deposit", status="pending_user_transfer_start"
        )
        print(f"deposits_to_receive: {len(deposits_to_receive)}")
        coroutines = [
            self.is_deposit_received(deposit) for deposit in deposits_to_receive
        ]
        results = await asyncio.gather(*coroutines, return_exceptions=True)
        received_deposits = []
        for deposit, result in zip(deposits_to_receive, results):
            if result is True:
                received_deposits.append(deposit)
            elif isinstance(result, Exception):
                logger.exception(result)
        await self.update_transactions(received_deposits, status="pending_anchor")

    async def task_send_deposits(self) -> None:
        deposits_received = await self.get_transactions(
            kind="deposit", status="pending_anchor"
        )
        print(f"deposits_received: {len(deposits_received)}")
        coroutines = [self.send_deposit(deposit) for deposit in deposits_received]
        results = await asyncio.gather(*coroutines, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.exception(result)

    async def task_poll_withdrawals_sent(self) -> None:
        withdrawals_sent = await self.get_transactions(
            kind="withdrawal", status="pending_external"
        )
        print(f"withdrawals_sent: {len(withdrawals_sent)}")
        coroutines = [
            self.is_withdrawal_complete(withdrawal) for withdrawal in withdrawals_sent
        ]
        results = await asyncio.gather(*coroutines, return_exceptions=True)
        completed_withdrawals = []
        for withdrawal, result in zip(withdrawals_sent, results):
            if result is True:
                completed_withdrawals.append(withdrawal)
            elif isinstance(result, Exception):
                logger.exception(result)
        await self.update_transactions(completed_withdrawals, status="completed")

    async def task_send_withdrawals(self) -> None:
        withdrawals_received = await self.get_transactions(
            kind="withdrawal", status="pending_anchor"
        )
        print(f"withdrawals_received: {len(withdrawals_received)}")
        coroutines = [
            self.send_withdrawal(withdrawal) for withdrawal in withdrawals_received
        ]
        await asyncio.gather(*coroutines, return_exceptions=True)

    async def watch_withdrawals_to_receive(self) -> None:
        withdrawals_to_receive = await self.get_transactions(
            kind="withdrawal", status="pending_user_transfer_start"
        )
        accounts = set([withdrawal.withdraw_anchor_account for withdrawal in withdrawals_to_receive])
        await asyncio.gather(
            *[
                self.stream_withdraw_anchor_account(account)
                for account in accounts
            ],
        )

    async def stream_withdraw_anchor_account(self, account: str):
        async with ServerAsync(
            horizon_url=self.horizon_url, client=AiohttpClient()
        ) as server:
            try:
                # Ensure the distribution account actually exists
                await server.load_account(account)
            except NotFoundError:
                # This exception will crash the process, but the anchor needs
                # to provide valid accounts to watch.
                raise RuntimeError(
                    "Stellar distribution account does not exist in horizon"
                )
            cursor = self.get_withdraw_anchor_account_cursor(account)
            if cursor is None:
                cursor = "0"

            endpoint = server.transactions().for_account(account).cursor(cursor)
            async for response in endpoint.stream():
                try:
                    await self.process_stream_response(response, account)
                except Exception as e:
                    logger.exception(e)

    async def process_stream_response(self, response, account: str):
        # We should not match valid pending transactions with ones that were
        # unsuccessful on the stellar network. If they were unsuccessful, the
        # client is also aware of the failure and will likely attempt to
        # resubmit it, in which case we should match the resubmitted transaction
        if not response.get("successful"):
            return

        try:
            _ = response["id"]
            envelope_xdr = response["envelope_xdr"]
            memo = response["memo"]
            result_xdr = response["result_xdr"]
        except KeyError:
            return

        transactions = await self.get_transactions(
            kind="withdrawal",
            status="pending_user_transfer_start",
            memo=memo,
            withdraw_anchor_account=account,
        )

        if not transactions:
            return
        elif len(transactions) > 1:
            raise ValueError(f"Found multiple transactions matching memo: {memo}")
        transaction = transactions[0]

        #TODO check if tx hash has already been processed (relevant if cursor is 0)

        op_results = TransactionResult.from_xdr(result_xdr).result.results
        horizon_tx = TransactionEnvelope.from_xdr(
            envelope_xdr, network_passphrase=self.network_passphrase,
        ).transaction

        payment_data, source = await self.find_matching_payment_data(
            response, horizon_tx, op_results, transaction
        )
        if payment_data is None:
            logger.info(f"Transaction matching memo {memo} has no payment operation")
            return

        await self.process_withdrawal_received(
            transaction=transaction,
            amount_received=payment_data["amount"],
            from_address=source,
            horizon_response=response,
        )

    async def find_matching_payment_data(
        self,
        response: Dict,
        horizon_tx: HorizonTransaction,
        result_ops: List[OperationResult],
        transaction: Sep24Transaction,
    ) -> Optional[Dict]:
        matching_payment_data = None
        source = None
        ops = horizon_tx.operations
        for idx, op_result in enumerate(result_ops):
            op, op_result = await self.cast_operation_and_result(ops[idx], op_result)
            if not op_result:  # not a payment op
                continue
            maybe_payment_data = await self.check_for_payment_match(
                op, op_result, transaction.asset
            )
            if maybe_payment_data:
                if ops[idx].source:
                    _source = ops[idx].source.account_muxed or ops[idx].source.account_id
                else:
                    _source = (
                        horizon_tx.source.account_muxed or horizon_tx.source.account_id
                    )
                matching_payment_data = maybe_payment_data
                source = _source
                break

        return matching_payment_data, source

    async def cast_operation_and_result(
        self, operation: Operation, op_result: OperationResult
    ) -> Tuple[Optional[PaymentOp], Optional[PaymentOpResult]]:
        op_xdr_obj = operation.to_xdr_object()
        if isinstance(operation, Payment):
            return (
                Payment.from_xdr_object(op_xdr_obj),
                op_result.tr.payment_result,
            )
        elif isinstance(operation, PathPaymentStrictSend):
            return (
                PathPaymentStrictSend.from_xdr_object(op_xdr_obj),
                op_result.tr.path_payment_strict_send_result,
            )
        elif isinstance(operation, PathPaymentStrictReceive):
            return (
                PathPaymentStrictReceive.from_xdr_object(op_xdr_obj),
                op_result.tr.path_payment_strict_receive_result,
            )
        else:
            return None, None

    async def check_for_payment_match(
        self, operation: PaymentOp, op_result: PaymentOpResult, transaction: Sep24Transaction
    ) -> Optional[Dict]:
        payment_data = await self.get_payment_values(operation, op_result)
        #TODO add doc saying these fields need to be set when creating the tx
        asset = await self.get_transaction_asset(transaction)
        if (
            payment_data["destination"] == transaction.withdraw_anchor_account
            and payment_data["code"] == asset.code
            and payment_data["issuer"] == asset.issuer
        ):
            return payment_data
        else:
            return None

    async def get_payment_values(
        self, operation: PaymentOp, op_result: PaymentOpResult
    ) -> Dict:
        values = {
            "destination": operation.destination.account_id,
            "amount": None,
            "code": None,
            "issuer": None,
        }
        if isinstance(operation, Payment):
            values["amount"] = str(operation.amount)
            values["code"] = operation.asset.code
            values["issuer"] = operation.asset.issuer
        elif isinstance(operation, PathPaymentStrictSend):
            # since the dest amount is not specified in a strict-send op,
            # we need to get the dest amount from the operation's result
            #
            # this method of fetching amounts gives the "raw" amount, so
            # we need to divide by Operation._ONE: 10000000
            # (Stellar uses 7 decimals places of precision)
            values["amount"] = from_xdr_amount(op_result.success.last.amount.int64)
            values["code"] = operation.dest_asset.code
            values["issuer"] = operation.dest_asset.issuer
        elif isinstance(operation, PathPaymentStrictReceive):
            values["amount"] = str(operation.dest_amount)
            values["code"] = operation.dest_asset.code
            values["issuer"] = operation.dest_asset.issuer
        else:
            raise ValueError("Unexpected operation, expected payment or path payment")
        return values

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
    ) -> Sep24Transaction:
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
    async def get_transactions(self,
        kind: Optional[Sep24TransactionKind] = None,
        status: Optional[Sep24TransactionStatus] = None,
        memo: Optional[str] = None,
        withdraw_anchor_account: Optional[str] = None,
    ) -> List[Sep24Transaction]:
        raise NotImplementedError()

    @abstractmethod
    async def get_transaction_asset(self, transaction: Sep24Transaction) -> Asset:
        raise NotImplementedError()

    @abstractmethod
    async def is_deposit_received(self, deposit: Sep24Transaction) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def is_withdrawal_complete(self, withdrawal: Sep24Transaction) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def process_withdrawal_received(self,
        transaction: Sep24Transaction,
        amount_received: str,
        from_address: str,
        horizon_response: Dict,
    ):
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

    @abstractmethod
    async def get_withdraw_anchor_account_cursor(self, account: str) -> Optional[str]:
        raise NotImplementedError()

