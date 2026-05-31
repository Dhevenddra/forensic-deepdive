// Intra-repo base types the heritage_sample below extends/implements.

export interface Named {
  name: string;
}

export interface Comparable<T> {
  compareTo(other: T): number;
}

export abstract class Widget {
  abstract render(): string;
}

export class Mix {
  mixed = true;
}
