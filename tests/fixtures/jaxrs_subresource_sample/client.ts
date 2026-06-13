// Consumer that joins a JAX-RS sub-resource route across the stack.
export async function loadItem(id: string) {
  return fetch(`/store/items/${id}/`);
}
