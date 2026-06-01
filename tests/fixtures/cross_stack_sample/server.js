const express = require("express");

const app = express();

app.get("/api/users/:id", getUser);
app.post("/api/users", createUser);

function getUser(req, res) {
  res.send(req.params.id);
}

function createUser(req, res) {
  res.send("ok");
}
