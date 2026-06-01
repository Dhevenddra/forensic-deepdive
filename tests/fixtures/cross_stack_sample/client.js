function loadUser(id) {
  return fetch(`/api/users/${id}`);
}

function addUser(data) {
  return axios.post("/api/users", data);
}

function listUsers() {
  return fetch("/api/users", { method: "GET" });
}

function removeUser(id) {
  return axios({ method: "delete", url: `/api/users/${id}` });
}

function ping() {
  return fetch("/health");
}

function dynamic(u) {
  return fetch(u);
}
