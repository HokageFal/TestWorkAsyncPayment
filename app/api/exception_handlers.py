from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.exceptions import PaymentAlreadyProcessed, PaymentNotFound


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(PaymentNotFound)
    async def payment_not_found_handler(
        request: Request,
        exc: PaymentNotFound,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": f"Payment {exc.payment_id} not found"},
        )

    @app.exception_handler(PaymentAlreadyProcessed)
    async def payment_already_processed_handler(
        request: Request,
        exc: PaymentAlreadyProcessed,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": f"Payment {exc.payment_id} already processed"},
        )
