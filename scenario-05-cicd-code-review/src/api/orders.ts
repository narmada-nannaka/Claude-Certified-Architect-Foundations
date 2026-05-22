import { OrderRepository } from "../repositories/OrderRepository";
import { logger } from "../utils/logger";

export async function processOrder(orderData) {
  logger.info("Processing order", { orderId: orderData.id });
  const repo = new OrderRepository();
  const result = await repo.save(orderData);
  return result;
}