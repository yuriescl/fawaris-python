import enum
from typing import Optional, List, Dict, Any


from typing_extensions import Literal
from pydantic import BaseModel, Field

class Sep9Customer(BaseModel):
    last_name: Optional[str]
    first_name: Optional[str]
    additional_name: Optional[str]
    address_country_code: Optional[str]
    state_or_province: Optional[str]
    city: Optional[str]
    postal_code: Optional[str]
    address: Optional[str]
    mobile_number: Optional[str]
    email_address: Optional[str]
    birth_date: Optional[str]
    birth_place: Optional[str]
    birth_country_code: Optional[str]
    bank_account_number: Optional[str]
    bank_number: Optional[str]
    bank_phone_number: Optional[str]
    bank_branch_number: Optional[str]
    tax_id: Optional[str]
    tax_id_name: Optional[str]
    occupation: Optional[str]
    employer_name: Optional[str]
    employer_address: Optional[str]
    language_code: Optional[str]
    id_type: Optional[str]
    id_country_code: Optional[str]
    id_issue_date: Optional[str]
    id_expiration_date: Optional[str]
    id_number: Optional[str]
    photo_id_front: Any
    photo_id_back: Any
    notary_approval_of_photo_id: Any
    ip_address: Optional[str]
    photo_proof_residence: Any
    sex: Optional[str]

class TransactionRefundsPayment(BaseModel):
    id: str
    id_type: str
    amount: str
    fee: str

class TransactionRefunds(BaseModel):
    amount_refunded: str
    amount_fee: str
    payments: List[TransactionRefundsPayment]

class TransactionRequiredInfoUpdates(BaseModel):
    transaction: Any

class Transaction(BaseModel):
    id: str
    kind: str
    status: Literal[
        "completed",
        "pending_external",
        "pending_anchor",
        "pending_stellar",
        "pending_trust",
        "pending_user",
        "pending_user_transfer_start",
        "pending_user_transfer_complete",
        "pending_customer_info_update",
        "pending_transaction_info_update",
        "incomplete",
        "no_market",
        "too_small",
        "too_large",
        "error",
    ]
    status_eta: Optional[int]
    more_info_url: Optional[str]
    amount_in: Optional[str]
    amount_in_asset: Optional[str]
    amount_out: Optional[str]
    amount_out_asset: Optional[str]
    amount_fee: Optional[str]
    amount_fee_asset: Optional[str]
    from_address: Optional[str] = Field(None, alias="from")
    to: Optional[str]
    external_extra: Optional[str]
    external_extra_text: Optional[str]
    deposit_memo: Optional[str]
    deposit_memo_type: Optional[str]
    withdraw_anchor_account: Optional[str]
    withdraw_memo: Optional[str]
    withdraw_memo_type: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    stellar_transaction_id: Optional[str]
    external_transaction_id: Optional[str]
    message: Optional[str]
    refunds: Optional[TransactionRefunds]
    required_info_message: Optional[str]
    required_info_updates: Optional[TransactionRequiredInfoUpdates]
    claimable_balance_id: Optional[str]



class Sep10GetRequest(BaseModel):
    """
    `GET <WEB_AUTH_ENDPOINT>` request schema
    """

    account: str
    home_domain: str
    memo: Optional[str] = None
    client_domain: Optional[str] = None


class Sep10GetResponse(BaseModel):
    """
    `GET <WEB_AUTH_ENDPOINT>` response schema
    """

    transaction: str
    network_passphrase: str


class Sep10PostRequest(BaseModel):
    """
    `POST <WEB_AUTH_ENDPOINT>` request schema
    """

    transaction: str


class Sep10PostResponse(BaseModel):
    """
    `POST <WEB_AUTH_ENDPOINT>` response schema
    """

    token: str


class Sep24DepositPostRequest(Sep9Customer, BaseModel):
    asset_code: str
    account: str
    asset_issuer: Optional[str]
    amount: Optional[str]
    memo_type: Optional[str]
    memo: Optional[str]
    wallet_name: Optional[str]
    wallet_url: Optional[str]
    lang: Optional[str] = "en"
    claimable_balance_supported: Optional[bool]

class Sep24WithdrawPostRequest(Sep9Customer, BaseModel):
    asset_code: str
    asset_issuer: Optional[str]
    amount: Optional[str]
    account: Optional[str]
    memo: Optional[str]
    memo_type: Optional[str]
    wallet_name: Optional[str]
    wallet_url: Optional[str]
    lang: Optional[str] = "en"

class Sep24DepositPostResponse(BaseModel):
    type: str = "interactive_customer_info_needed"
    url: str
    id: str

class Sep24PostResponse(BaseModel):
    type: str = "interactive_customer_info_needed"
    url: str
    id: str

class Sep24InfoRequest(BaseModel):
    lang: Optional[str] = "en"

class Sep24InfoResponseDeposit(BaseModel):
    enabled: bool
    min_amount: Optional[str]
    max_amount: Optional[str]
    fee_fixed: Optional[str]
    fee_percent: Optional[str]
    fee_minimum: Optional[str]

class Sep24InfoResponseWithdraw(BaseModel):
    enabled: bool
    min_amount: Optional[str]
    max_amount: Optional[str]
    fee_fixed: Optional[str]
    fee_percent: Optional[str]
    fee_minimum: Optional[str]

class Sep24InfoResponseFee(BaseModel):
    authentication_required: bool
    enabled: bool

class Sep24InfoResponseFeatures(BaseModel):
    account_creation: bool
    claimable_balances: bool

class Sep24InfoResponse(BaseModel):
    deposit: Dict[str, Sep24InfoResponseDeposit]
    withdraw: Dict[str, Sep24InfoResponseWithdraw]
    fee: Sep24InfoResponseFee
    features: Sep24InfoResponseFeatures

class Sep24FeeRequest(BaseModel):
    operation: str
    asset_code: str
    amount: str
    type: Optional[str]

class Sep24FeeResponse(BaseModel):
    operation: str
    asset_code: str
    amount: str
    type: Optional[str]
