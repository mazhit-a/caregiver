/** Access to the fixtures captured from the real backend (`src/test/fixtures/app/*.json`). */
const modules = import.meta.glob("../fixtures/app/*.json", { eager: true, import: "default" });

const byName = new Map<string, unknown>(
  Object.entries(modules).map(([file, value]) => [
    file.slice(file.lastIndexOf("/") + 1).replace(/\.json$/, ""),
    value,
  ]),
);

export const APP_FIXTURE_NAMES: string[] = [...byName.keys()].sort();

/** A fresh deep copy, so a test or a fake can change it without touching the shared object. */
export function appFixture<T = unknown>(name: string): T {
  if (!byName.has(name)) throw new Error(`No app fixture named "${name}".`);
  return structuredClone(byName.get(name)) as T;
}
