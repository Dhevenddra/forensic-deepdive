// Tiny Java fixture for the v0.2 tags + graph layer.
package sample;

public class Greeter implements Named {
    private final String name;

    public Greeter(String name) {
        this.name = name;
    }

    @Override
    public String name() {
        return name;
    }

    public String greet() {
        return formatMessage(name);
    }

    private static String formatMessage(String n) {
        return "hello, " + n;
    }
}

interface Named {
    String name();
}

enum Severity {
    LOW,
    HIGH
}
