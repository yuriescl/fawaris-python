from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse
from stellar_sdk import Network, Keypair
import fawaris

from sep24 import Sep24

app = FastAPI()

CLIENT_SECRET = "SBLZPFTQY74COGBRJYKC6Y3X46KDYO46BPBRZK27IXUQ73DP6IDNUB7X"
SEP10 = fawaris.Sep10(
    host_url="http://localhost",
    home_domains=["localhost"],
    horizon_url="https://horizon-testnet.stellar.org",
    network_passphrase=Network.TESTNET_NETWORK_PASSPHRASE,
    signing_secret="SD3ME2YQNWQYBKYX7KNMX5C42WTWMZRZD7DH72K63B56G636AYBQH7YY",
    jwt_key="jwtsecret",
)
SEP24 = Sep24(sep10_jwt_key="jwtsecret")

@app.exception_handler(Exception)
async def exception_handler(request, exc):
    return JSONResponse({"error": str(exc)}, status_code=500)

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse({"error": str(exc)}, status_code=400)

@app.exception_handler(fawaris.Sep10InvalidToken)
async def sep10_invalid_token_handler(request, exc):
    return JSONResponse({"type": "authentication_required"}, status_code=403)

@app.get("/auth")
async def http_get_auth(request: Request):
    params = dict(request.query_params)
    if not params.get("home_domain"):
        params["home_domain"] = "localhost"
    return await SEP10.http_get(fawaris.Sep10GetRequest(**params))


@app.post("/auth")
async def http_post_auth(request: Request):
    data = await detect_and_get_request_data(request, allowed_content_types=[
        "application/x-www-form-urlencoded", "application/json"
    ])
    return await SEP10.http_post(fawaris.Sep10PostRequest(**data))


@app.post("/sep24/transactions/deposit/interactive")
async def http_post_transactions_deposit_interactive(request: Request):
    token = request.headers.get("authorization").split(" ")[1]
    # TODO check token account? https://github.com/stellar/django-polaris/issues/604 data = await detect_and_get_request_data(request)
    data = await detect_and_get_request_data(request)
    return await SEP24.http_post_transactions_deposit_interactive(
        fawaris.Sep24DepositPostRequest(**data), sep10_encoded_jwt=token
    )


@app.post("/sep24/transactions/withdraw/interactive")
async def http_post_transactions_withdraw_interactive(request: Request):
    # TODO handle invalid authorization format
    token = request.headers.get("authorization").split(" ")[1]
    # TODO check token account? https://github.com/stellar/django-polaris/issues/604
    data = await detect_and_get_request_data(request)
    return await SEP24.http_post_transactions_withdraw_interactive(
        fawaris.Sep24WithdrawPostRequest(**data), sep10_encoded_jwt=token
    )


async def detect_and_get_request_data(
    request: Request,
    allowed_content_types=[
        "multipart/form-data",
        "application/x-www-form-urlencoded",
        "application/json",
    ],
):
    content_type = request.headers.get("content-type")
    allowed = False
    for allowed_content_type in allowed_content_types:
        if allowed_content_type in content_type:
            allowed = True
    if not allowed:
        raise ValueError("Header 'Content-Type' has an invalid value")
    if "multipart/form-data" in content_type:
        data = await request.form()
    elif "application/x-www-form-urlencoded" in content_type:
        data = await request.form()
    elif "application/json" in content_type:
        data = await request.json()
    return data
