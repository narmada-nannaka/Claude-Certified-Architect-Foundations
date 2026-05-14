import { z } from "zod";

const OrderSchema = z.object({
  orderId: z.string(),
  customerId: z.string(),
  amountUsd: z.number().positive(),
});

export async function getOrder(orderId: string) {
  try {
    const response = await fetch(`/api/internal/orders/${orderId}`);
    if (!response.ok) {
      return {
        ok: false as const,
        errorCategory: response.status >= 500 ? "transient" : "validation",
        message: `Failed to fetch order ${orderId}`,
      };
    }
    const data = await response.json();
    return { ok: true as const, order: OrderSchema.parse(data) };
  } catch (err) {
    return {
      ok: false as const,
      errorCategory: "transient",
      message: err instanceof Error ? err.message : "Unknown error",
    };
  }
}