from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse
from stellar_sdk import Network, Keypair
from pydantic.error_wrappers import ValidationError
import fawaris

import sep10
import sep24

app = FastAPI()

JWT_KEY = "jwtsecret"
CLIENT_SECRET = "SBLZPFTQY74COGBRJYKC6Y3X46KDYO46BPBRZK27IXUQ73DP6IDNUB7X"
SEP10 = fawaris.Sep10(
    host_url="http://localhost",
    home_domains=["localhost"],
    horizon_url="https://horizon-testnet.stellar.org",
    network_passphrase=Network.TESTNET_NETWORK_PASSPHRASE,
    signing_secret="SD3ME2YQNWQYBKYX7KNMX5C42WTWMZRZD7DH72K63B56G636AYBQH7YY",
    jwt_key=JWT_KEY,
)
SEP24 = sep24.Sep24(sep10_jwt_key=JWT_KEY)

sep10.add_routes(app, SEP10)
sep24.add_routes(app, SEP24)

@app.exception_handler(Exception)
async def exception_handler(request, exc):
    return JSONResponse({"error": str(exc)}, status_code=500)

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    msg = str(exc)
    if isinstance(exc, ValidationError):
        msg = ""
        for error in exc.errors():
            if error["type"] == "value_error.missing":
                try:
                    field = error["loc"][0]
                    msg += f"Missing value for '{field}'"
                except (KeyError, IndexError):
                    msg += str(error) + ". "
            else:
                msg += str(error) + ". "
    return JSONResponse({"error": msg}, status_code=400)

@app.exception_handler(fawaris.Sep10InvalidToken)
async def sep10_invalid_token_handler(request, exc):
    return JSONResponse({"type": "authentication_required"}, status_code=403)
