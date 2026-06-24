class PaymentNotFound(Exception):
    def __init__(self, payment_id: str) -> None:
        self.payment_id = payment_id
        super().__init__(f"Payment {payment_id} not found")


class PaymentAlreadyProcessed(Exception):
    def __init__(self, payment_id: str) -> None:
        self.payment_id = payment_id
        super().__init__(f"Payment {payment_id} already processed")
