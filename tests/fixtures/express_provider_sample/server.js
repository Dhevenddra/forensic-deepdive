const express = require("express");

const app = express();
const router = express.Router();

app.get("/users/:id", (req, res) => {
  res.send(req.params.id);
});

app.post("/users", createUser);

router.get("/", listItems);
router.delete("/:itemId", removeItem);

app.use("/api/items", router);

app.get("/health", (req, res) => res.send("ok"));

function createUser(req, res) {
  res.send("created");
}

function listItems(req, res) {
  res.send([]);
}

function removeItem(req, res) {
  res.send("removed");
}
