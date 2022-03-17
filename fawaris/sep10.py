from typing import Optional, List, Dict
from urllib.parse import urlparse

from pydantic import BaseModel, Field
import toml
from stellar_sdk.sep.stellar_web_authentication import (
    build_challenge_transaction,
    read_challenge_transaction,
    verify_challenge_transaction_threshold,
    verify_challenge_transaction_signed_by_client_master_key,
)
from stellar_sdk import Keypair, MuxedAccount
from stellar_sdk.sep.stellar_toml import fetch_stellar_toml
from stellar_sdk.sep.exceptions import (
    InvalidSep10ChallengeError,
    StellarTomlNotFoundError,
)
from stellar_sdk.exceptions import (
    NotFoundError,
    ConnectionError,
    Ed25519PublicKeyInvalidError,
)
from stellar_sdk.client.requests_client import RequestsClient

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

class Sep10:
    def __init__(
        self,
        web_auth_domain: str,
        signing_seed: str,
        network_passphrase: str,
    ):
        """
        Implementation of `SEP0010 <https://github.com/stellar/stellar-protocol/blob/master/ecosystem/sep-0010.md>`_

        @param web_auth_domain: Web auth domain, must match WEB_AUTH_ENDPOINT from
            this Anchor's stellar.toml. For example, if
            WEB_AUTH_ENDPOINT=https://mysep10.domain.com, then this variable must
            be set to mysep10.domain.com
        @param signing_seed: Challenge transaction signing seed, which is the
            secret key of the public key SIGNING_KEY from this Anchor's
            stellar.toml"
        @param network_passphrase: Network passphrase, must be the same as
            NETWORK_PASSPHRASE from this Anchor's stellar.toml
        """
        self.web_auth_domain = web_auth_domain
        self.signing_seed = signing_seed
        self.network_passphrase = network_passphrase

    def build_challenge_transaction(
        self,
        request: Sep10GetRequest,
        home_domains_allowed: Optional[List[str]] = None,
        client_domain_required: bool = False,
        client_domains_allowed: Optional[List[str]] = None,
        client_domains_denied: Optional[List[str]] = None,
        timeout: int = 900,
    ) -> Sep10GetResponse:
        """
        Returns a XDR-encoded SEP-10 challenge transaction

        :param home_domains_allowed: List of allowed home_domain values when
            building challenge transaction. If not set, any home_domain is
            accepted
        :param client_domain_required: Require client_domain when building
            challenge transaction
        :param client_domains_allowed: List of allowed client_domain values.
            If not set, any client_domain is accepted
        :param client_domains_denied: List of denied client_domain values.
            If not set, any client_domain is accepted. If a client_domain is
            listed both here and in client_domains_allowed, it will be denied
        :param timeout: Challenge duration in seconds (default is 15 minutes)

        :raises: :exc:`ValueError`:
        """
        memo = request.memo
        if memo:
            try:
                memo = int(memo)
            except ValueError:
                raise ValueError(
                    "invalid 'memo' value. Expected a 64-bit integer."
                )
            if request.account.startswith("M"):
                raise ValueError(
                    "'memo' cannot be passed with a muxed client account "
                    "address (M...)"
                )
        else:
            memo = None

        if home_domains_allowed is not None:
            if request.home_domain not in home_domains_allowed:
                raise ValueError(
                    "invalid 'home_domain' value. Accepted values: "
                    f"{self.allowed_home_domains}"
                )

        if (
            urlparse(f"https://{request.home_domain}").netloc
            != request.home_domain
        ):
            raise ValueError("'home_domain' must be a valid hostname")

        if request.client_domain:
            if (
                urlparse(f"https://{request.client_domain}").netloc
                != request.client_domain
            ):
                raise ValueError("'client_domain' must be a valid hostname")

            if (
                client_domains_denied is not None
                and request.client_domain in client_domains_denied
            ):
                raise ValueError("'client_domain' value is denied")

            if (
                client_domains_allowed is not None
                and request.client_domain not in client_domains_allowed
            ):
                raise ValueError("'client_domain' value is not allowed")

            try:
                client_signing_key = self.get_client_signing_key(request.client_domain)
            except (
                ConnectionError,
                StellarTomlNotFoundError,
                toml.decoder.TomlDecodeError,
            ):
                raise ValueError("unable to fetch 'client_domain' SIGNING_KEY")

        else:
            if client_domain_required:
                raise ValueError("'client_domain' is required")
            client_domain = None
            client_signing_key = None

        transaction = build_challenge_transaction(
            server_secret=self.signing_seed,
            client_account_id=request.account,
            home_domain=request.home_domain,
            web_auth_domain=self.web_auth_domain,
            network_passphrase=self.network_passphrase,
            timeout=timeout,
            client_domain=request.client_domain,
            client_signing_key=client_signing_key,
            memo=memo,
        )
        return Sep10GetResponse(
            transaction=transaction,
            network_passphrase=self.network_passphrase,
        )

    def get_client_signing_key(self, client_domain, request_timeout=11):
        client_toml_contents = fetch_stellar_toml(
            client_domain,
            client=RequestsClient(request_timeout=request_timeout),
        )
        client_signing_key = client_toml_contents.get("SIGNING_KEY")
        if not client_signing_key:
            raise ValueError("SIGNING_KEY not present on 'client_domain' TOML")
        try:
            Keypair.from_public_key(client_signing_key)
        except Ed25519PublicKeyInvalidError:
            raise ValueError("invalid SIGNING_KEY value on 'client_domain' TOML")
        return client_signing_key
