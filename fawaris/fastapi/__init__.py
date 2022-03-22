from typing import Optional
from fastapi import FastAPI

import fawaris
from fawaris.fastapi.sep10 import register_routes as sep10_register_routes
from fawaris.fastapi.sep24 import register_routes as sep24_register_routes


def register_routes(
    app: FastAPI,
    sep10: Optional[fawaris.Sep10] = None,
    sep24: Optional[fawaris.Sep24] = None,
):
    if sep10 is not None:
        sep10_register_routes(app, sep10)
    if sep24 is not None:
        sep24_register_routes(app, sep24)
