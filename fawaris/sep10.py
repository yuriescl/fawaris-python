from typing import Optional, List, Dict, Union, Iterable, Callable, Any
from urllib.parse import urlparse
from datetime import datetime, timezone
import logging
import os
import os.path

import jwt
from jwt import decode
from jwt.exceptions import InvalidTokenError
import toml
from stellar_sdk.sep.stellar_web_authentication import (
    build_challenge_transaction,
    read_challenge_transaction,
    verify_challenge_transaction_threshold,
    verify_challenge_transaction_signed_by_client_master_key,
)
from stellar_sdk.operation import ManageData
from stellar_sdk import ServerAsync, Keypair, MuxedAccount
from stellar_sdk.sep.stellar_toml import fetch_stellar_toml
from stellar_sdk.sep.exceptions import (
    InvalidSep10ChallengeError,
    StellarTomlNotFoundError,
)
from stellar_sdk.exceptions import (
    NotFoundError,
    ConnectionError,
    Ed25519PublicKeyInvalidError,
    Ed25519SecretSeedInvalidError,
    MuxedEd25519AccountInvalidError,
    ValueError as StellarSdkValueError,
)
from stellar_sdk.client.aiohttp_client import AiohttpClient
from stellar_sdk.strkey import StrKey

from fawaris.models import (
    Sep10GetRequest,
    Sep10GetResponse,
    Sep10PostRequest,
    Sep10PostResponse,
)
from fawaris.exceptions import Sep10InvalidToken

logger = logging.getLogger(__name__)

class Sep10:
    host_url: str
    home_domains: Union[str, Iterable[str]]
    horizon_url: str
    network_passphrase: str
    signing_secret: str
    jwt_secret: str
    client_domain_required: bool
    client_domains_allowed: Optional[List[str]]
    client_domains_denied: Optional[List[str]]

    server_account_id: str
    web_auth_domain: str

    def __init__(
        self,
        host_url: str,
        home_domains: Union[str, Iterable[str]],
        horizon_url: str,
        network_passphrase: str,
        signing_secret: str,
        jwt_secret: str,
        client_domain_required: bool = False,
        client_domains_allowed: Optional[List[str]] = None,
        client_domains_denied: Optional[List[str]] = None,
    ):
        """
        Implementation of `SEP0010 <https://github.com/stellar/stellar-protocol/blob/master/ecosystem/sep-0010.md>`_

        :param host_url: URL to this Anchor instance, ex: https://myanchor.domain.com
        :param home_domains: The home domain that is expected to be included
            in the first Manage Data operation's string key. If a list is
            provided, one of the domain names in the array must match.
        :param horizon_url: Stellar API url, ex: https://horizon-testnet.stellar.org
        :param network_passphrase: Network passphrase, must be the same as
            NETWORK_PASSPHRASE from this Anchor's stellar.toml
        :param signing_secret: Challenge transaction signing seed, which is the
            secret key of the public key SIGNING_KEY from this Anchor's
            stellar.toml
        :param jwt_secret: JWT secret key used to encode the JWT
        :param client_domain_required: Require client_domain when building
            challenge transaction
        :param client_domains_allowed: List of allowed client_domain values.
            If not set, any client_domain is accepted
        :param client_domains_denied: List of denied client_domain values.
            If not set, any client_domain is accepted. If a client_domain is
            listed both here and in client_domains_allowed, it will be denied
        """
        if not urlparse(host_url).netloc:
            raise ValueError(f"{host_url} is not a valid host_url")
        self.host_url = host_url
        self.web_auth_domain = urlparse(host_url).netloc

        self.home_domains = home_domains
        self.horizon_url = horizon_url
        self.network_passphrase = network_passphrase

        try:
            kp = Keypair.from_secret(signing_secret)
        except Ed25519SecretSeedInvalidError:
            raise ValueError("'signing_secret' contains an invalid secret key")
        self.signing_secret = signing_secret
        self.server_account_id = kp.public_key

        self.jwt_secret = jwt_secret
        self.client_domain_required = client_domain_required
        self.client_domains_allowed = client_domains_allowed
        self.client_domains_denied = client_domains_denied

    async def http_get(
        self,
        request: Sep10GetRequest,
        timeout: int = 900,
    ) -> Sep10GetResponse:
        memo = request.memo
        if memo:
            try:
                memo = int(memo)
            except ValueError:
                raise ValueError("invalid 'memo' value. Expected a 64-bit integer.")
            if request.account.startswith("M"):
                raise ValueError(
                    "'memo' cannot be passed with a muxed client account "
                    "address (M...)"
                )
        else:
            memo = None

        if request.home_domain not in self.home_domains:
            raise ValueError(
                "invalid 'home_domain' value. Accepted values: " f"{self.home_domains}"
            )

        if urlparse(f"https://{request.home_domain}").netloc != request.home_domain:
            raise ValueError("'home_domain' must be a valid hostname")

        if request.client_domain:
            if (
                urlparse(f"https://{request.client_domain}").netloc
                != request.client_domain
            ):
                raise ValueError("'client_domain' must be a valid hostname")

            if (
                self.client_domains_denied is not None
                and request.client_domain in self.client_domains_denied
            ):
                raise ValueError("'client_domain' value is denied")

            if (
                self.client_domains_allowed is not None
                and request.client_domain not in self.client_domains_allowed
            ):
                raise ValueError("'client_domain' value is not allowed")

            try:
                client_signing_key = await self._get_client_signing_key(
                    request.client_domain
                )
            except (
                ConnectionError,
                StellarTomlNotFoundError,
                toml.decoder.TomlDecodeError,
            ):
                raise ValueError("unable to fetch 'client_domain' SIGNING_KEY")

        else:
            if self.client_domain_required:
                raise ValueError("'client_domain' is required")
            client_domain = None
            client_signing_key = None

        transaction = build_challenge_transaction(
            server_secret=self.signing_secret,
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

    async def http_post(self, request: Sep10PostRequest) -> Sep10PostResponse:
        client_domain = await self._validate_challenge_xdr(request)
        return Sep10PostResponse(token=self._generate_jwt(request, client_domain))

    def _get_http_client(self, request_timeout=11):
        return AiohttpClient(request_timeout=request_timeout)

    async def _get_client_signing_key(self, client_domain):
        client_toml_contents = await fetch_stellar_toml(
            client_domain,
            client=self._get_http_client(),
        )
        client_signing_key = client_toml_contents.get("SIGNING_KEY")
        if not client_signing_key:
            raise ValueError("SIGNING_KEY not present on 'client_domain' TOML")
        try:
            Keypair.from_public_key(client_signing_key)
        except Ed25519PublicKeyInvalidError:
            raise ValueError("invalid SIGNING_KEY value on 'client_domain' TOML")
        return client_signing_key

    async def _validate_challenge_xdr(self, request: Sep10GetRequest):
        logger.debug("Validating challenge transaction")
        try:
            challenge = read_challenge_transaction(
                challenge_transaction=request.transaction,
                server_account_id=self.server_account_id,
                home_domains=self.home_domains,
                web_auth_domain=self.web_auth_domain,
                network_passphrase=self.network_passphrase,
            )
        except (InvalidSep10ChallengeError, TypeError) as e:
            raise ValueError(e)

        client_domain = None
        for operation in challenge.transaction.transaction.operations:
            if (
                isinstance(operation, ManageData)
                and operation.data_name == "client_domain"
            ):
                client_domain = operation.data_value.decode()
                break

        # extract the Stellar account from the muxed account to check for its existence
        stellar_account = challenge.client_account_id
        if challenge.client_account_id.startswith("M"):
            stellar_account = MuxedAccount.from_account(
                challenge.client_account_id
            ).account_id

        try:
            async with ServerAsync(
                horizon_url=self.horizon_url, client=self._get_http_client()
            ) as server:
                account = await server.load_account(stellar_account)
        except NotFoundError:
            logger.debug("Account does not exist, using client's master key to verify")
            try:
                verify_challenge_transaction_signed_by_client_master_key(
                    challenge_transaction=request.transaction,
                    server_account_id=self.server_account_id,
                    home_domains=self.home_domains,
                    web_auth_domain=self.web_auth_domain,
                    network_passphrase=self.network_passphrase,
                )
                if (client_domain and len(challenge.transaction.signatures) != 3) or (
                    not client_domain and len(challenge.transaction.signatures) != 2
                ):
                    raise InvalidSep10ChallengeError(
                        "There is more than one client signer on a challenge "
                        "transaction for an account that doesn't exist"
                    )
            except InvalidSep10ChallengeError as e:
                raise ValueError(
                    f"Missing or invalid signature(s) for {challenge.client_account_id}: {str(e)}"
                )
            else:
                logger.debug("Challenge verified using client's master key")
                return client_domain

        signers = account.load_ed25519_public_key_signers()
        threshold = account.thresholds.med_threshold
        signers_found = verify_challenge_transaction_threshold(
            challenge_transaction=request.transaction,
            server_account_id=self.server_account_id,
            home_domains=self.home_domains,
            web_auth_domain=self.web_auth_domain,
            network_passphrase=self.network_passphrase,
            threshold=threshold,
            signers=signers,
        )
        logger.debug(
            f"Challenge verified using account signers: {[s.account_id for s in signers_found]}"
        )

        return client_domain

    def _generate_jwt(
        self, request: Sep10PostRequest, client_domain: str = None
    ) -> str:
        challenge = read_challenge_transaction(
            challenge_transaction=request.transaction,
            server_account_id=self.server_account_id,
            home_domains=self.home_domains,
            web_auth_domain=self.web_auth_domain,
            network_passphrase=self.network_passphrase,
        )
        logger.debug(f"Generating SEP-10 token for account {challenge.client_account_id}")

        # set iat value to minimum timebound of the challenge so that the JWT returned
        # for a given challenge is always the same.
        # https://github.com/stellar/stellar-protocol/pull/982
        issued_at = challenge.transaction.transaction.time_bounds.min_time

        # format sub value based on muxed account or memo
        if challenge.client_account_id.startswith("M") or not challenge.memo:
            sub = challenge.client_account_id
        else:
            sub = f"{challenge.client_account_id}:{challenge.memo}"

        jwt_dict = {
            "iss": os.path.join(self.host_url, "auth"),
            "sub": sub,
            "iat": issued_at,
            "exp": issued_at + 24 * 60 * 60,
            "jti": challenge.transaction.hash().hex(),
            "client_domain": client_domain,
        }
        return jwt.encode(jwt_dict, self.jwt_secret, algorithm="HS256")

class Sep10Token:
    """
    SEP-10 token representation.
    See https://github.com/stellar/django-polaris/blob/v2.2.0/polaris/polaris/sep10/token.py
    """

    _REQUIRED_FIELDS = {"iss", "sub", "iat", "exp"}

    def __init__(self, jwt: Union[str, Dict], jwt_secret):
        if isinstance(jwt, str):
            try:
                jwt = decode(jwt, jwt_secret, algorithms=["HS256"])
            except InvalidTokenError as e:
                raise Sep10InvalidToken("unable to decode jwt" + str(e))
        elif not isinstance(jwt, Dict):
            raise Sep10InvalidToken(
                "invalid type for 'jwt' parameter: must be a string or dictionary"
            )

        if not self._REQUIRED_FIELDS.issubset(set(jwt.keys())):
            raise Sep10InvalidToken(
                f"jwt is missing one of the required fields: {', '.join(self._REQUIRED_FIELDS)}"
            )

        memo = None
        stellar_account = None
        if jwt["sub"].startswith("M"):
            try:
                StrKey.decode_muxed_account(jwt["sub"])
            except (MuxedEd25519AccountInvalidError, StellarSdkValueError):
                raise Sep10InvalidToken(f"invalid muxed account address: {jwt['sub']}")
        elif ":" in jwt["sub"]:
            try:
                stellar_account, memo = jwt["sub"].split(":")
            except ValueError:
                raise Sep10InvalidToken(f"improperly formatted 'sub' value: {jwt['sub']}")
        else:
            stellar_account = jwt["sub"]

        if stellar_account:
            try:
                Keypair.from_public_key(stellar_account)
            except Ed25519PublicKeyInvalidError:
                raise Sep10InvalidToken(f"invalid Stellar public key: {jwt['sub']}")

        if memo:
            try:
                int(memo)
            except ValueError:
                raise Sep10InvalidToken(
                    f"invalid memo in 'sub' value, expected 64-bit integer: {memo}"
                )

        try:
            iat = datetime.fromtimestamp(jwt["iat"], tz=timezone.utc)
        except (OSError, ValueError, OverflowError):
            raise Sep10InvalidToken("invalid iat value")
        try:
            exp = datetime.fromtimestamp(jwt["exp"], tz=timezone.utc)
        except (OSError, ValueError, OverflowError):
            raise Sep10InvalidToken("invalid exp value")

        now = datetime.now(tz=timezone.utc)
        if now < iat or now > exp:
            raise Sep10InvalidToken("jwt is no longer valid")

        client_domain = jwt.get("client_domain")
        if (
            client_domain
            and urlparse(f"https://{client_domain}").netloc != client_domain
        ):
            raise Sep10InvalidToken("'client_domain' must be a hostname")

        self._payload = jwt

    @property
    def account(self) -> str:
        """
        The Stellar account (`G...`) authenticated. Note that a muxed account
        could have been authenticated, in which case `Token.muxed_account` should
        be used.
        """
        if self._payload["sub"].startswith("M"):
            return MuxedAccount.from_account(self._payload["sub"]).account_id
        elif ":" in self._payload["sub"]:
            return self._payload["sub"].split(":")[0]
        else:
            return self._payload["sub"]

    @property
    def muxed_account(self) -> Optional[str]:
        """
        The M-address specified in the payload's ``sub`` value, if present
        """
        return self._payload["sub"] if self._payload["sub"].startswith("M") else None

    @property
    def memo(self) -> Optional[int]:
        """
        The memo included with the payload's ``sub`` value, if present
        """
        return (
            int(self._payload["sub"].split(":")[1])
            if ":" in self._payload["sub"]
            else None
        )

    @property
    def issuer(self) -> str:
        """
        The principal that issued a token, RFC7519, Section 4.1.1 — a Uniform
        Resource Identifier (URI) for the issuer
        (https://example.com or https://example.com/G...)
        """
        return self._payload["iss"]

    @property
    def issued_at(self) -> datetime:
        """
        The time at which the JWT was issued RFC7519, Section 4.1.6 -
        represented as a UTC datetime object
        """
        return datetime.fromtimestamp(self._payload["iat"], tz=timezone.utc)

    @property
    def expires_at(self) -> datetime:
        """
        The expiration time on or after which the JWT will not accepted for
        processing, RFC7519, Section 4.1.4 — represented as a UTC datetime object
        """
        return datetime.fromtimestamp(self._payload["exp"], tz=timezone.utc)

    @property
    def client_domain(self) -> Optional[str]:
        """
        A nonstandard JWT claim containing the client's home domain, included if
        the challenge transaction contained a ``client_domain`` ManageData operation
        """
        return self._payload.get("client_domain")

    @property
    def payload(self) -> dict:
        """
        The decoded contents of the JWT string
        """
        return self._payload
