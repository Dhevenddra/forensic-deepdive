import React from "react";
import { Named, Comparable, Widget, Mix } from "./base";

// interface -> interface extends (multiple) — was dropped before DEC-050.
export interface Animal extends Named {
  legs: number;
}
export interface Pet extends Animal, Comparable<Pet> {
  owner: string;
}

// abstract class with heritage — abstract_class_declaration was dropped before.
export abstract class Shape extends Widget implements Named {
  name = "shape";
}

// generic_type and member_expression heritage targets — both dropped before.
export class Button extends React.Component<Props> implements Comparable<Button> {
  render() {
    return "button";
  }
}

// simple-case regression guard: plain identifier extends + implements.
export class Card extends Widget implements Named, Mix {
  name = "card";
  mixed = true;
}
