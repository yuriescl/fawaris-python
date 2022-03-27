import asyncio
import unittest
from stellar_sdk import Network, Keypair, TransactionEnvelope
from fawaris import Sep10, Sep10GetRequest, Sep10PostRequest


class TestSep10(unittest.TestCase):
    def test_sep10(self):
        async def _async():
            server_signing_secret = (
                "SALAW2MR7I7L47W5ZKJXJMGUZSKRSTVUQ7O3ZHEZ6O7MUKLDGWZ5U2JW"
            )
            client_account_secret = (
                "SBLZPFTQY74COGBRJYKC6Y3X46KDYO46BPBRZK27IXUQ73DP6IDNUB7X"
            )

            sep10 = Sep10(
                "http://localhost",
                ["localhost"],
                "https://horizon-testnet.stellar.org",
                Network.TESTNET_NETWORK_PASSPHRASE,
                server_signing_secret,
                "jwtsecret",
            )

            client_kp = Keypair.from_secret(client_account_secret)
            resp = await sep10.http_get(
                Sep10GetRequest(
                    account=client_kp.public_key,
                    home_domain="localhost",
                )
            )

            envelope_xdr = resp.transaction
            envelope = TransactionEnvelope.from_xdr(
                envelope_xdr, Network.TESTNET_NETWORK_PASSPHRASE
            )
            client_signing_key = Keypair.from_secret(client_account_secret)
            envelope.sign(client_signing_key)
            client_signed_envelope_xdr = envelope.to_xdr_object().to_xdr()

            resp = await sep10.http_post(
                Sep10PostRequest(transaction=client_signed_envelope_xdr)
            )
            assert resp.token

        asyncio.run(_async())


if __name__ == "__main__":
    unittest.main()
