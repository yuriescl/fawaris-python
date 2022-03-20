from overrides import overrides
import fawaris


class Sep24(fawaris.Sep24):
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
    async def http_get_fee(self, request, sep10_encoded_jwt=None) -> fawaris.Sep24FeeResponse:
        raise NotImplementedError()

    @overrides
    async def create_transaction(self, request, sep10_token):
        if isinstance(request, fawaris.Sep24DepositPostRequest):
            return fawaris.Transaction(
                id="transaction1",
                kind="deposit",
                status="pending_user_transfer_start",
            )
        elif isinstance(request, fawaris.Sep24WithdrawPostRequest):
            return fawaris.Transaction(
                id="transaction1",
                kind="withdrawal",
                status="pending_user_transfer_start",
            )

    @overrides
    async def get_interactive_url(self, request, sep10_token, tx):
        return "https://testanchor.domain.com"
