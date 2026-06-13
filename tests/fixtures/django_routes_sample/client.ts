// Frontend consumer (DEC-065 fixture) — joins the Django routes across the stack.

export async function loadVets() {
  return fetch('/api/v1/vets/');
}

export async function createOwner(body: object) {
  return fetch('/api/v1/owners/', { method: 'POST', body: JSON.stringify(body) });
}
