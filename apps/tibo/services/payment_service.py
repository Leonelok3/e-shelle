import os

from apps.tibo.models import Payment


class PaymentService:
    @staticmethod
    def create_stripe_checkout(order, success_url, cancel_url):
        try:
            import stripe
        except ImportError as exc:
            raise RuntimeError("Installez stripe pour activer le checkout Stripe.") from exc
        stripe.api_key = os.getenv("TIBO_STRIPE_SECRET_KEY") or os.getenv("STRIPE_SECRET_KEY", "")
        if not stripe.api_key:
            raise RuntimeError("TIBO_STRIPE_SECRET_KEY est manquant.")
        session = stripe.checkout.Session.create(
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=order.email,
            line_items=[
                {
                    "price_data": {
                        "currency": order.currency.lower(),
                        "product_data": {"name": f"Commande {order.number}"},
                        "unit_amount": int(order.total * 100),
                    },
                    "quantity": 1,
                }
            ],
            metadata={"order_id": str(order.id), "order_number": order.number},
        )
        Payment.objects.create(
            order=order,
            provider=Payment.STRIPE,
            status=Payment.PENDING,
            amount=order.total,
            currency=order.currency,
            provider_reference=session.id,
            raw_response=session,
        )
        return session

    @staticmethod
    def create_paypal_order(order):
        Payment.objects.create(
            order=order,
            provider=Payment.PAYPAL,
            status=Payment.PENDING,
            amount=order.total,
            currency=order.currency,
        )
        return {"status": "created", "order": order.number}

