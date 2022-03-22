from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse
from stellar_sdk import Network, Keypair
from pydantic.error_wrappers import ValidationError
import fawaris

from fawaris.fastapi import register_routes

def example_app():
    app = FastAPI()

    JWT_KEY = "@)wqgb)3&e6k&(l8hfm(3wt8=*_x$w@vc$4)&nbih-&2eg9dlh"
    CLIENT_SECRET = "SBLZPFTQY74COGBRJYKC6Y3X46KDYO46BPBRZK27IXUQ73DP6IDNUB7X"
    sep10 = fawaris.Sep10(
        host_url="http://localhost",
        home_domains=["localhost"],
        horizon_url="https://horizon-testnet.stellar.org",
        network_passphrase=Network.TESTNET_NETWORK_PASSPHRASE,
        signing_secret="SD3ME2YQNWQYBKYX7KNMX5C42WTWMZRZD7DH72K63B56G636AYBQH7YY",
        jwt_key=JWT_KEY,
    )
    sep24 = fawaris.Sep24(sep10_jwt_key=JWT_KEY)
    register_routes(app, sep10=sep10, sep24=sep24)
    return app

def example_app_with_database():
    if database is not None:
        @app.on_event("startup")
        async def startup():
            await database.connect()

        @app.on_event("shutdown")
        async def shutdown():
            await database.disconnect()

