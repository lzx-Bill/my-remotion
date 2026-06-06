import { z } from "zod";
import { zColor } from "@remotion/zod-types";

export const sectionStyleSchema = z.enum(["story", "modern", "chalkboard"]);

export const beachSchema = z.object({
  sun: z.object({ x: z.number(), y: z.number(), r: z.number() }),
  sandColor: zColor(),
  skyTop: zColor(),
  skyBottom: zColor(),
});

export const geoColorsSchema = z.object({
  a: zColor(),
  b: zColor(),
  c: zColor(),
  triangle: zColor(),
});

export const sectionSchema = z.object({
  id: z.string(),
  style: sectionStyleSchema,
  title: z.string(),
  durationS: z.number().positive(),
  script: z.string(),
  cta: z.string().optional(),
});
export type SectionData = z.infer<typeof sectionSchema>;

export const tripleSchema = z.object({
  a: z.number(),
  b: z.number(),
  c: z.number(),
  color: zColor(),
});

export const primitiveTripleSchema = z.object({
  a: z.number(),
  b: z.number(),
  c: z.number(),
  formula: z.string(),
  m: z.number(),
  n: z.number(),
});

export const geometricIntuitionSchema = z.object({
  a: z.number(),
  b: z.number(),
  c: z.number(),
});

export const pythagoreanSchema = z.object({
  title: z.string(),
  subtitle: z.string(),
  tagline: z.string(),
  accentColor: zColor(),
  modernBg: zColor(),
  chalkboardBg: zColor(),
  storyBg: zColor(),
  beach: beachSchema,
  geoColors: geoColorsSchema,
  triples: z.array(tripleSchema),
  primitiveTriples: z.array(primitiveTripleSchema),
  geometricIntuition: geometricIntuitionSchema,
  sections: z.array(sectionSchema),
});

export type PythagoreanData = z.infer<typeof pythagoreanSchema>;
