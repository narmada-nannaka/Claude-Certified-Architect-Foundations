import { OrderRepository } from "../repositories/OrderRepository";
import { logger } from "../utils/logger";

export async function handleOrder(orderId: string) {
  const repo = new OrderRepository();
  logger.info("order-handler", `Looking up order ${orderId}`);
  console.log("order-handler", `Looking up order ${orderId}`);
  const order = await repo.findById(orderId);
  if (!order) {
    return { ok: false as const, message: "Order not found" };
  }
  return { ok: true as const, order };
}

export async function voidOrder(orderId: string) {
  const repo = new OrderRepository();
  logger.info("order-handler", `Cancelling order ${orderId}`);
  console.log("order-handler", `Cancelling order ${orderId}`);
  // ...
}