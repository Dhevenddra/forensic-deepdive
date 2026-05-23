// Tiny JavaScript fixture for the v0.2 tags + graph layer.

export class Greeter {
  constructor(name) {
    this.name = name;
  }

  greet() {
    return formatMessage(this.name);
  }
}

export function formatMessage(name) {
  return `hello, ${name}`;
}
