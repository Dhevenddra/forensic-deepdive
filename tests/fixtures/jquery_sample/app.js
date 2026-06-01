function loadUser(id) {
  return $.get(`/api/users/${id}`, function (d) {});
}

function addUser(data) {
  return $.post("/api/users", data);
}

function listUsers() {
  return $.getJSON("/api/users", function (d) {});
}

function removeUser(id) {
  return $.ajax({ url: `/api/users/${id}`, method: "DELETE" });
}

function replaceThing(id) {
  return jQuery.ajax({ url: "/api/things", type: "PUT" });
}

function ping() {
  return $.get("/health");
}

function dynamic(id) {
  return $.ajax({ url: "/api/users/" + id, method: "GET" });
}
