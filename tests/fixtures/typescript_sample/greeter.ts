// Tiny TypeScript fixture for the v0.2 tags + graph layer.

export interface Named {
  name: string;
}

export class Greeter implements Named {
  constructor(public readonly name: string) {}

  greet(): string {
    return formatMessage(this.name);
  }
}

export function formatMessage(name: string): string {
  return `hello, ${name}`;
}
