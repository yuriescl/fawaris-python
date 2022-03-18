import asyncio
import unittest
from stellar_sdk import Network, Keypair, TransactionEnvelope
from fawaris.sep10 import Sep10, Sep10GetRequest, Sep10PostRequest


class TestSep10(unittest.TestCase):
    def test_sep10(self):
        async def _async():
            sep10 = Sep10(
                "http://localhost",
                ["localhost"],
                "https://horizon-testnet.stellar.org",
                Network.TESTNET_NETWORK_PASSPHRASE,
                "SD3ME2YQNWQYBKYX7KNMX5C42WTWMZRZD7DH72K63B56G636AYBQH7YY",
                "jwtsecret",
            )
            resp = await sep10.get(
                Sep10GetRequest(
                    account="GACGKVS4ECC2UUECHQGWPO5YY66T7FDPTEBTDD4X445APZPWWT5YPRMP",
                    home_domain="localhost",
                )
            )
            envelope_xdr = resp.transaction
            envelope = TransactionEnvelope.from_xdr(
                envelope_xdr, Network.TESTNET_NETWORK_PASSPHRASE
            )
            client_signing_key = Keypair.from_secret(
                "SAXTOCC6EYFF7EJQJETNRTUQTM4PGYXWO3O4BCNDGEQ3EJHNX4MBY2Y6"
            )
            envelope.sign(client_signing_key)
            client_signed_envelope_xdr = envelope.to_xdr_object().to_xdr()
            request = Sep10PostRequest(transaction=client_signed_envelope_xdr)
            resp = await sep10.post(request)
            assert resp.token

        asyncio.run(_async())


if __name__ == "__main__":
    unittest.main()
