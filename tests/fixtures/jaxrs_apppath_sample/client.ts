// Consumer that joins a JAX-RS route carrying the @ApplicationPath prefix.
export async function loadGreetings() {
  return fetch("/api/greetings");
}
