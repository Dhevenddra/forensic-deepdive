package sample

func Run() {
	g := &Greeter{name: "world"}
	_ = g.Greet()
	_ = formatMessage("again")
}
