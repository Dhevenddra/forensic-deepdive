// Frontend consumers — join the NestJS + JAX-RS routes via ROUTES_TO.

export function loadCat(id) {
  return fetch(`/cats/${id}`);
}

export function createOwner() {
  return fetch('/owners', { method: 'POST' });
}
