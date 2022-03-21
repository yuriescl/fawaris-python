import sqlalchemy

metadata = sqlalchemy.MetaData()

transactions = sqlalchemy.Table(
    "transactions",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Text, primary_key=True),
    sqlalchemy.Column("kind", sqlalchemy.Text),
    sqlalchemy.Column("status", sqlalchemy.Text),
    sqlalchemy.Column("status_eta", sqlalchemy.Integer),
    sqlalchemy.Column("more_info_url", sqlalchemy.Text),
    sqlalchemy.Column("amount_in", sqlalchemy.Text),
    sqlalchemy.Column("amount_in_asset", sqlalchemy.Text),
    sqlalchemy.Column("amount_out", sqlalchemy.Text),
    sqlalchemy.Column("amount_out_asset", sqlalchemy.Text),
    sqlalchemy.Column("amount_fee", sqlalchemy.Text),
    sqlalchemy.Column("amount_fee_asset", sqlalchemy.Text),
    sqlalchemy.Column("from", sqlalchemy.Text),
    sqlalchemy.Column("to", sqlalchemy.Text),
    sqlalchemy.Column("external_extra", sqlalchemy.Text),
    sqlalchemy.Column("external_extra_text", sqlalchemy.Text),
    sqlalchemy.Column("deposit_memo", sqlalchemy.Text),
    sqlalchemy.Column("deposit_memo_type", sqlalchemy.Text),
    sqlalchemy.Column("withdraw_anchor_account", sqlalchemy.Text),
    sqlalchemy.Column("withdraw_memo", sqlalchemy.Text),
    sqlalchemy.Column("withdraw_memo_type", sqlalchemy.Text),
    sqlalchemy.Column("started_at", sqlalchemy.Text),
    sqlalchemy.Column("completed_at", sqlalchemy.Text),
    sqlalchemy.Column("stellar_transaction_id", sqlalchemy.Text),
    sqlalchemy.Column("external_transaction_id", sqlalchemy.Text),
    sqlalchemy.Column("message", sqlalchemy.Text),
    refunds: Optional[Sep24TransactionRefunds]
    sqlalchemy.Column("required_info_message", sqlalchemy.Text),
    required_info_updates: Optional[Sep24TransactionRequiredInfoUpdates]
    sqlalchemy.Column("claimable_balance_id", sqlalchemy.Text),
)
