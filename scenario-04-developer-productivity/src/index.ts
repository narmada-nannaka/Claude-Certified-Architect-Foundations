import { handleOrder } from "./handlers/order-handler";
import { handleUser } from "./handlers/user-handler";
import { handleBilling } from "./handlers/billing-handler";

export const handlers = {
  order: handleOrder,
  user: handleUser,
  billing: handleBilling,
};