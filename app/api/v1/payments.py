import uuid

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_idempotency_key, verify_api_key
from app.database import get_db
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.services.payment import PaymentService

router = APIRouter(
    prefix="/api/v1/payments",
    tags=["payments"],
    dependencies=[Depends(verify_api_key)],
)


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=PaymentResponse,
)
async def create_payment(
    body: PaymentCreate,
    idempotency_key: str = Depends(get_idempotency_key),
    session: AsyncSession = Depends(get_db),
) -> PaymentResponse | JSONResponse:
    service = PaymentService(session)
    response, is_new = await service.create(body, idempotency_key)
    if not is_new:
        return JSONResponse(
            content=response.model_dump(mode="json"),
            status_code=status.HTTP_202_ACCEPTED,
        )
    return response


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    service = PaymentService(session)
    return await service.get(payment_id)
