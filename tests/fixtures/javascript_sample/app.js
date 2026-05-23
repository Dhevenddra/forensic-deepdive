import { Greeter, formatMessage } from "./greeter.js";

function main() {
  const g = new Greeter("world");
  console.log(g.greet());
  console.log(formatMessage("again"));
}

main();
