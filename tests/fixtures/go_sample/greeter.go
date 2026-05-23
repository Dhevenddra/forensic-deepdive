// Tiny Go fixture for the v0.2 tags + graph layer.
package sample

import "fmt"

type Greeter struct {
	name string
}

type Named interface {
	Name() string
}

func (g *Greeter) Name() string {
	return g.name
}

func (g *Greeter) Greet() string {
	return formatMessage(g.name)
}

func formatMessage(name string) string {
	return fmt.Sprintf("hello, %s", name)
}
