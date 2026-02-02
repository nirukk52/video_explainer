import path from "node:path";
import { config } from "dotenv";
import { defineConfig } from "drizzle-kit";

// Load root .env first (for POSTGRES_URL), then .env.local for overrides
config({ path: path.resolve(__dirname, "..", ".env") });
config({ path: ".env.local" });

export default defineConfig({
  schema: "./lib/db/schema.ts",
  out: "./lib/db/migrations",
  dialect: "postgresql",
  dbCredentials: {
    // biome-ignore lint: Forbidden non-null assertion.
    url: process.env.POSTGRES_URL!,
  },
});
