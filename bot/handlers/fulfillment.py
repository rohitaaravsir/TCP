"""
bot/handlers/fulfillment.py

Fulfillment utility for confirming orders and delivering digital assets (PDFs).
"""

from __future__ import annotations

import logging
from aiogram import Bot
from services.order_service import OrderService, OrderServiceError
from services.product_service import ProductService
from schemas.order import OrderStatus

logger = logging.getLogger(__name__)


async def fulfill_and_notify_order(
    order_id: int,
    order_service: OrderService,
    product_service: ProductService | None,
    bot: Bot,
) -> None:
    """
    Confirm an order, check for digital assets (file_id PDF), and deliver them.
    """
    try:
        # Confirm the order via service
        order = await order_service.confirm_order(order_id)
        
        # Try to deliver digital product if product_service is available
        product = None
        if product_service:
            try:
                product = await product_service.get_product(order.product_id)
            except Exception as prod_exc:
                logger.error(
                    "Failed to fetch product details for fulfillment | order_id=%s | error=%s",
                    order_id, prod_exc,
                )

        # Check if digital delivery is possible
        if product and product.file_id:
            try:
                # Deliver the file (PDF)
                await bot.send_document(
                    chat_id=order.user_id,
                    document=product.file_id,
                    caption=(
                        f"🎉 <b>Payment Confirmed & Delivered!</b>\n\n"
                        f"📦 Order ID: <code>{order.id}</code>\n"
                        f"🏷️ Product: <b>{product.name}</b>\n"
                        f"💰 Amount: {order.amount_display}\n\n"
                        f"Please find your digital product attached. Thank you for your purchase! ❤️"
                    ),
                    parse_mode="HTML",
                )
                # Mark as delivered
                await order_service.mark_delivered(order_id)
                logger.info(
                    "Digital product delivered successfully | order_id=%s | user_id=%s",
                    order_id, order.user_id,
                )
                return
            except Exception as deliver_exc:
                logger.error(
                    "Failed to deliver digital product file | order_id=%s | file_id=%s | error=%s",
                    order_id, product.file_id, deliver_exc,
                )

        # Fallback/standard confirmation message (for manual processing or if delivery failed)
        await bot.send_message(
            chat_id=order.user_id,
            text=(
                f"🎉 <b>Payment Approved!</b>\n\n"
                f"📦 Order ID: <code>{order.id}</code>\n"
                f"💰 Amount: {order.amount_display}\n"
                f"🔖 Status: {order.status_display}\n\n"
                f"Your order is now being processed. Thank you for your purchase!"
            ),
            parse_mode="HTML",
        )
        logger.info(
            "Buyer notified of payment approval | order_id=%s | buyer_id=%s",
            order_id, order.user_id,
        )

    except OrderServiceError as exc:
        logger.error("Order fulfillment failed | order_id=%s | error=%s", order_id, exc)
        raise
