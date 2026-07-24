import { z } from "zod";

export const TelegramUserSchema = z.object({
  telegram_id: z.number(),
  first_name: z.string(),
  last_name: z.string().nullable().optional(),
  username: z.string().nullable().optional(),
  language_code: z.string().nullable().optional(),
  is_premium: z.boolean().optional(),
  allows_write_to_pm: z.boolean().nullable().optional(),
  photo_url: z.string().nullable().optional(),
});

export const TelegramValidateResponseSchema = z.object({
  status: z.literal("valid"),
  auth_date: z.number(),
  user: TelegramUserSchema,
});

export const UserProfileSchema = TelegramUserSchema.extend({
  id: z.string().uuid(),
  created_at: z.string(),
  updated_at: z.string(),
});

export type TelegramUser = z.infer<typeof TelegramUserSchema>;
export type TelegramValidateResponse = z.infer<typeof TelegramValidateResponseSchema>;
export type UserProfile = z.infer<typeof UserProfileSchema>;

export type TelegramValidationState =
  | "idle"
  | "validating"
  | "valid"
  | "invalid"
  | "unavailable"
  | "browser";
