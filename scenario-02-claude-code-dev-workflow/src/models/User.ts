import { drizzle } from "drizzle-orm";

export class UserRepository {
  constructor(private db: ReturnType<typeof drizzle>) {}

  async findById(userId: string) {
    // Repository methods follow {entity}Repository.{verb}{Noun} pattern
    return this.db.query.users.findFirst({
      where: (users, { eq }) => eq(users.id, userId),
    });
  }

  async findByEmail(email: string) {
    return this.db.query.users.findFirst({
      where: (users, { eq }) => eq(users.email, email),
    });
  }
}