from fastapi import APIRouter, Depends
from models.order import Order, OrderItem
from models.product import Product
from schemas.order import PostOrder
from routes.auth import authenticate
from tortoise.transactions import in_transaction
from datetime import datetime


order_router = APIRouter()


@order_router.post("/orders")
async def post_order(schema: PostOrder):
    async with in_transaction() as conn:
        new_order = Order(client_name=schema.client_name, client_phone=schema.client_phone,
                          client_address=schema.client_address)
        await new_order.save(using_db=conn)

        total_price = 0

        for item in schema.items:
            product_price = await Product.filter(id=item.product_id).first().values('price')
            if product_price is not None:
                total_price += product_price['price'] * item.quantity
                new_order_item = OrderItem(product_id=item.product_id, quantity=item.quantity, order_id=new_order.id)
                await new_order_item.save(using_db=conn)
            else:
                return {"success": False,
                        "error": "product not found"}

        await Order.filter(id=new_order.id).update(total_price=total_price)

    return {"success": True,
            "id": new_order.id}


@order_router.get("/orders")
async def get_orders(authenticated: dict = Depends(authenticate)):
    if authenticated:
        orders = await Order.all().order_by("-date")
        orders_dicts = []
        for order in orders:
            order_dict = order.__dict__
            items = await OrderItem.filter(order_id=order.id).all().values('product__id', 'product__name', 'quantity')
            order_dict['items'] = items
            orders_dicts.append(order_dict)
        return {
            "success": True,
            "orders": orders_dicts
        }
    else:
        return {"success": False,
                "error": "not authenticated"}


@order_router.delete("/orders/{order_id}")
async def delete_order(order_id: int, authenticated: dict = Depends(authenticate)):
    if authenticated:
        await Order.filter(id=order_id).delete()
        return {"success": True}
    else:
        return {"success": False,
                "error": "not authenticated"}
