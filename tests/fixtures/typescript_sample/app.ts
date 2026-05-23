import { Greeter, formatMessage } from "./greeter";

function main(): void {
  const g = new Greeter("world");
  console.log(g.greet());
  console.log(formatMessage("again"));
}

main();
